import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, MapPin, Calendar, Users, DollarSign, Heart, Compass, MessageSquare, Bot, User, Loader2 } from 'lucide-react';

const TravelRecommender = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'system',
      content: "Welcome to your AI-powered Sri Lankan travel companion! ✈️ I'll help you discover the perfect seasonal destinations across the pearl of the Indian Ocean. Tell me about your dream trip!",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e?.preventDefault?.();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: input.trim() }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: data.output.summary || 'Sorry, I encountered an issue processing your request.',
        status: data.output.status,
        format: data.output.format,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: 'Sorry, I\'m having trouble connecting right now. Please try again in a moment.',
        status: 'error',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatMarkdown = (text) => {
    if (!text) return '';

    return text
      // Headers
      .replace(/^### (.*$)/gm, '<h3 class="text-lg font-semibold text-gray-800 mt-4 mb-2">$1</h3>')
      .replace(/^## (.*$)/gm, '<h2 class="text-xl font-bold text-gray-900 mt-6 mb-3 border-b border-gray-200 pb-1">$1</h2>')
      .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold text-gray-900 mt-6 mb-4">$1</h1>')
      // Bold text
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>')
      // Bullet points
      .replace(/^- (.*$)/gm, '<li class="ml-4 mb-1">• $1</li>')
      // Line breaks
      .replace(/\n/g, '<br />');
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'complete':
      case 'completed':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      case 'awaiting_user_input':
        return 'text-amber-600';
      default:
        return 'text-blue-600';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'complete':
      case 'completed':
        return <Heart className="w-4 h-4" />;
      case 'error':
        return <Sparkles className="w-4 h-4" />;
      case 'awaiting_user_input':
        return <MessageSquare className="w-4 h-4" />;
      default:
        return <Compass className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-white/20 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
                <MapPin className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Sri Lanka Travel AI</h1>
              <p className="text-sm text-gray-600">Your seasonal travel companion</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 hover:bg-white/80 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-medium text-gray-700">Seasonal Planning</span>
            </div>
          </div>
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 hover:bg-white/80 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium text-gray-700">Group Travel</span>
            </div>
          </div>
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 hover:bg-white/80 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <DollarSign className="w-5 h-5 text-purple-600" />
              <span className="text-sm font-medium text-gray-700">Budget Friendly</span>
            </div>
          </div>
          <div className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 hover:bg-white/80 transition-all duration-300">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-amber-600" />
              <span className="text-sm font-medium text-gray-700">AI Powered</span>
            </div>
          </div>
        </div>

        {/* Chat Container */}
        <div className="bg-white/70 backdrop-blur-md rounded-3xl border border-white/20 shadow-2xl overflow-hidden">
          {/* Messages */}
          <div className="h-96 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex items-start space-x-3 max-w-3xl ${message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                    message.type === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-purple-500'
                      : message.type === 'system'
                      ? 'bg-gradient-to-r from-green-500 to-teal-500'
                      : 'bg-gradient-to-r from-orange-500 to-red-500'
                  }`}>
                    {message.type === 'user' ? (
                      <User className="w-4 h-4 text-white" />
                    ) : (
                      <Bot className="w-4 h-4 text-white" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div className={`relative group ${message.type === 'user' ? 'text-right' : ''}`}>
                    <div className={`px-4 py-3 rounded-2xl ${
                      message.type === 'user'
                        ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                        : message.type === 'system'
                        ? 'bg-gradient-to-r from-green-100 to-teal-100 text-gray-800 border border-green-200'
                        : 'bg-gray-50 text-gray-800 border border-gray-200'
                    } shadow-lg hover:shadow-xl transition-all duration-300`}>
                      {message.format === 'markdown' && message.type === 'bot' ? (
                        <div
                          className="prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{ __html: formatMarkdown(message.content) }}
                        />
                      ) : (
                        <p className="text-sm leading-relaxed">{message.content}</p>
                      )}

                      {message.status && message.type === 'bot' && (
                        <div className={`flex items-center space-x-1 mt-2 pt-2 border-t border-gray-200 ${getStatusColor(message.status)}`}>
                          {getStatusIcon(message.status)}
                          <span className="text-xs font-medium capitalize">{message.status}</span>
                        </div>
                      )}
                    </div>

                    {/* Timestamp */}
                    <div className={`text-xs text-gray-500 mt-1 ${message.type === 'user' ? 'text-right' : ''}`}>
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-r from-orange-500 to-red-500 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-50 px-4 py-3 rounded-2xl border border-gray-200">
                    <div className="flex items-center space-x-2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                      <span className="text-sm text-gray-600">Crafting your perfect Sri Lankan adventure...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 p-6 bg-white/80 backdrop-blur-sm">
            <div className="flex space-x-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
                  placeholder="Describe your ideal trip to Sri Lanka..."
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all duration-300 text-sm placeholder-gray-500"
                  disabled={isLoading}
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <Sparkles className="w-4 h-4 text-gray-400" />
                </div>
              </div>

              <button
                type="button"
                onClick={handleSubmit}
                disabled={isLoading || !input.trim()}
                className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-2xl font-medium hover:from-blue-700 hover:to-purple-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg hover:shadow-xl group"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5 group-hover:translate-x-0.5 transition-transform duration-200" />
                )}
              </button>
            </div>

            <p className="text-xs text-gray-500 mt-3 text-center">
              Powered by AI • Discover the wonders of Sri Lanka through every season
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TravelRecommender;