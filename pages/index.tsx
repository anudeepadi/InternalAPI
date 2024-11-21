import type { NextPage } from 'next'
import Head from 'next/head'
import { useState, useEffect } from 'react'
import { useClaudeApi, Organization } from '@/hooks/useClaudeApi'

const Home: NextPage = () => {
  const { getOrganizations, streamChat, loading, error } = useClaudeApi();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');

  useEffect(() => {
    async function fetchOrgs() {
      try {
        const orgs = await getOrganizations();
        setOrganizations(orgs);
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to fetch organizations';
        console.error('Error:', errorMessage);
      }
    }
    fetchOrgs();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim() || !organizations[0]?.id) return;

    setResponse('');
    try {
      for await (const chunk of streamChat(organizations[0].id, message)) {
        if ('completion' in chunk && typeof chunk.completion === 'string') {
          setResponse(prev => prev + chunk.completion);
        }
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Chat error occurred';
      console.error('Chat error:', errorMessage);
    }
  }

  return (
    <>
      <Head>
        <title>ClaudeAPI</title>
        <meta name="description" content="Claude API Integration" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900">
              ClaudeAPI
            </h1>
            <p className="mt-4 text-xl text-gray-600">
              Your Claude.ai API integration
            </p>
          </div>

          {error && (
            <div className="mb-8 p-4 bg-red-50 text-red-700 rounded-md">
              {error}
            </div>
          )}

          <div className="max-w-2xl mx-auto">
            <form onSubmit={handleSubmit} className="space-y-4">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full h-32 p-4 border rounded-md"
                placeholder="Enter your message..."
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !message.trim() || organizations.length === 0}
                className="w-full py-2 px-4 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-gray-400"
              >
                {loading ? 'Sending...' : 'Send Message'}
              </button>
              {organizations.length === 0 && (
                <p className="text-sm text-gray-500 text-center">No organizations available</p>
              )}
            </form>

            {response && (
              <div className="mt-8">
                <h2 className="text-xl font-semibold mb-4">Response:</h2>
                <div className="p-4 bg-white rounded-md shadow whitespace-pre-wrap">
                  {response}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  )
}

export default Home