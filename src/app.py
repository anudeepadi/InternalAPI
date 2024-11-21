import streamlit as st
import requests
import json
from datetime import datetime, timezone, timedelta

# Configure page
st.set_page_config(
    page_title="ClaudeSync",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stTextInput>div>div>input {
        background-color: white;
    }
    .stChatMessage {
        background-color: white !important;
        padding: 1rem !important;
        border-radius: 0.5rem !important;
    }
    .user-message {
        background-color: #E8F0FE !important;
        margin: 1rem 0;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #000000;
    }
    .assistant-message {
        background-color: #F8F9FA !important;
        margin: 1rem 0;
        padding: 1rem;
        border-radius: 0.5rem;
        color: #000000;
    }
    .streaming-response {
        background-color: #F8F9FA !important;
        margin: 1rem 0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #7C4DFF;
        color: #000000;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'session_key' not in st.session_state:
    st.session_state.session_key = None
if 'current_org_id' not in st.session_state:
    st.session_state.current_org_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None

API_BASE_URL = "http://127.0.0.1:8000"

def display_message(content, message_type="assistant"):
    """Display a message with proper styling"""
    if message_type == "user":
        st.markdown(f'<div class="user-message">👤 You: {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">🤖 Claude: {content}</div>', unsafe_allow_html=True)

def process_stream_data(line):
    """Process a single line of SSE data"""
    try:
        if line.startswith('data: '):
            data_str = line[6:]  # Remove 'data: ' prefix
            if data_str == '[DONE]':
                return None
            data = json.loads(data_str)
            if 'completion' in data:
                return data['completion']
    except json.JSONDecodeError:
        pass
    return None

def make_request(endpoint, method="GET", data=None, stream=False):
    """Make an API request"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {st.session_state.session_key}"
    }
    
    try:
        response = requests.request(
            method=method,
            url=f"{API_BASE_URL}{endpoint}",
            json=data,
            headers=headers,
            stream=stream
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def login(session_key):
    """Authenticate with the API"""
    try:
        expiry = datetime.now(timezone.utc) + timedelta(days=365)
        expiry_str = expiry.strftime("%a, %d %b %Y %H:%M:%S UTC")
        
        response = make_request(
            "/auth/login",
            method="POST",
            data={"session_key": session_key, "expires": expiry_str}
        )
        
        if response and response.status_code == 200:
            st.session_state.session_key = session_key
            st.session_state.authenticated = True
            return True
        return False
    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        return False

def get_organizations():
    """Fetch organizations"""
    response = make_request("/organizations")
    if response:
        return response.json()
    return []

def create_chat(org_id, project_uuid=None):
    """Create a new chat"""
    response = make_request(
        f"/organizations/{org_id}/chats",
        method="POST",
        data={"project_uuid": project_uuid}
    )
    if response:
        return response.json()
    return None

def send_message(org_id, chat_id, message):
    """Send a message and handle streaming response"""
    try:
        response = make_request(
            f"/organizations/{org_id}/chats/{chat_id}/messages",
            method="POST",
            data={"prompt": message},
            stream=True
        )
        
        if not response:
            return None

        # Create a container for the streaming response
        with st.container():
            # Display user message immediately
            display_message(message, "user")
            
            # Create placeholder for assistant's response
            response_placeholder = st.empty()
            full_response = ""

            # Process the streaming response
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    completion = process_stream_data(decoded_line)
                    if completion is not None:
                        full_response += completion
                        # Update the response placeholder
                        response_placeholder.markdown(
                            f'<div class="streaming-response">🤖 Claude: {full_response}</div>',
                            unsafe_allow_html=True
                        )

        return full_response

    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return None

def main():
    st.title("🤖 ClaudeSync")

    # Login form
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                session_key = st.text_input(
                    "Enter your Claude.ai session key",
                    type="password",
                    help="Your session key should start with 'sk-ant-'"
                )
                submitted = st.form_submit_button("Login", use_container_width=True)
                
                if submitted and session_key:
                    if login(session_key):
                        st.success("Successfully logged in!")
                        st.rerun()

    else:
        # Get organizations
        organizations = get_organizations()
        
        if organizations:
            # Sidebar for organization selection
            with st.sidebar:
                st.title("Organizations")
                org_names = {org['id']: org['name'] for org in organizations}
                
                selected_org = st.selectbox(
                    "Select Organization",
                    options=list(org_names.keys()),
                    format_func=lambda x: org_names[x]
                )
                
                if selected_org:
                    st.session_state.current_org_id = selected_org
                    
                    if st.button("New Chat", use_container_width=True):
                        new_chat = create_chat(selected_org)
                        if new_chat:
                            st.session_state.current_chat_id = new_chat.get('uuid')
                            st.session_state.chat_history = []
                            st.rerun()
                
                if st.button("Logout", use_container_width=True):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()

            # Main chat area
            if st.session_state.current_chat_id:
                # Display chat history
                chat_container = st.container()
                with chat_container:
                    for msg_type, content in st.session_state.chat_history:
                        display_message(content, msg_type)

                # Chat input
                if prompt := st.chat_input("Type your message here"):
                    # Add user message to history
                    st.session_state.chat_history.append(("user", prompt))
                    
                    # Send message and get response
                    response = send_message(
                        selected_org,
                        st.session_state.current_chat_id,
                        prompt
                    )
                    
                    if response:
                        st.session_state.chat_history.append(("assistant", response))
                        st.rerun()
            else:
                st.info("👈 Click 'New Chat' in the sidebar to start a conversation!")

        else:
            st.warning("No organizations found. Please check your connection and try again.")

if __name__ == "__main__":
    main()