import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './LandingPage.css';

const LandingPage = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isSignInOpen, setIsSignInOpen] = useState(false);
  const [isSignUpOpen, setIsSignUpOpen] = useState(false);
  const navigate = useNavigate();
  const { login, signup, user, logout } = useAuth();

  // Form states
  const [signInData, setSignInData] = useState({
    login: '',
    password: ''
  });

  const [signUpData, setSignUpData] = useState({
    username: '',
    name: '',
    email: '',
    password: ''
  });

  const [signInError, setSignInError] = useState('');
  const [signUpError, setSignUpError] = useState('');
  const [isSignInLoading, setIsSignInLoading] = useState(false);
  const [isSignUpLoading, setIsSignUpLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      type: 'bot',
      content: `Hello! 👋 I'm your personal travel assistant. I can help you with:
• Finding the best destinations
• Planning your itinerary  
• Booking flights & hotels
• Getting travel tips

What would you like to know about Sri Lanka?`
    }
  ]);
  const [chatInput, setChatInput] = useState('');

  const openModal = (type) => {
    if (type === 'signin') {
      setIsSignInOpen(true);
      setSignInError('');
      setSignInData({ login: '', password: '' });
    }
    if (type === 'signup') {
      setIsSignUpOpen(true);
      setSignUpError('');
      setSignUpData({ username: '', name: '', email: '', password: '' });
    }
  };

  const closeModal = (type) => {
    if (type === 'signin') {
      setIsSignInOpen(false);
      setSignInError('');
      setSignInData({ login: '', password: '' });
    }
    if (type === 'signup') {
      setIsSignUpOpen(false);
      setSignUpError('');
      setSignUpData({ username: '', name: '', email: '', password: '' });
    }
  };

  const switchModal = (from, to) => {
    closeModal(from);
    openModal(to);
  };

  // Handle Sign In
  const handleSignIn = async (e) => {
    e.preventDefault();
    setSignInError('');
    setIsSignInLoading(true);

    try {
      await login(signInData);
      setIsSignInOpen(false);
      navigate('/chat');
    } catch (error) {
      setSignInError(error.message || 'Login failed. Please try again.');
    } finally {
      setIsSignInLoading(false);
    }
  };

  // Handle Sign Up
  const handleSignUp = async (e) => {
    e.preventDefault();
    setSignUpError('');
    setIsSignUpLoading(true);

    try {
      await signup(signUpData);
      setIsSignUpOpen(false);
      navigate('/chat');
    } catch (error) {
      setSignUpError(error.message || 'Registration failed. Please try again.');
    } finally {
      setIsSignUpLoading(false);
    }
  };

  const toggleChat = () => {
    setIsChatOpen(!isChatOpen);
  };

  const generateAIResponse = (userInput) => {
    const responses = {
      'sigiriya': '🏛️ Sigiriya is amazing! I recommend visiting early morning (6 AM) to avoid crowds. The climb takes 2-3 hours. Would you like me to check availability for guided tours?',
      'temple': '🕉️ The Temple of the Sacred Tooth is perfect for cultural experiences! Visit during Puja ceremonies (5:30 AM, 9:30 AM, 6:30 PM). I can arrange a cultural guide for you.',
      'tea': '🍃 Nuwara Eliya is beautiful! Best time is April-September. I suggest the scenic train ride from Kandy. Want me to book train tickets and tea plantation tours?',
      'galle': '🏰 Galle Fort is magical at sunset! Stay 2-3 days to explore fully. I can find you charming boutique hotels within the fort walls.',
      'price': '💰 Great news! We have special packages starting from $299 for 5 days. With our current 40% discount, that\'s just $179! Shall I show you the details?',
      'book': '📅 I\'d love to help you book! First, let me ask: What dates are you thinking? How many travelers? What\'s your budget range?',
      'default': '🤖 That\'s a great question! I specialize in Sri Lankan travel. I can help with destinations, bookings, itineraries, and travel tips. What specifically would you like to know?'
    };
    
    const input = userInput.toLowerCase();
    for (let key in responses) {
      if (input.includes(key)) {
        return responses[key];
      }
    }
    return responses['default'];
  };

  const sendMessage = () => {
    if (chatInput.trim() === '') return;
    
    // Add user message
    const newMessages = [...chatMessages, { type: 'user', content: chatInput }];
    setChatMessages(newMessages);
    
    // Simulate AI response
    setTimeout(() => {
      const botResponse = generateAIResponse(chatInput);
      setChatMessages(prev => [...prev, { type: 'bot', content: botResponse }]);
    }, 1000);
    
    setChatInput('');
  };

  const handleChatKeyPress = (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  };

  return (
    <div>
      <header>
        <div className="container">
          <div className="header-content">
            <div className="logo">Travling!</div>
            <nav>
              <ul style={{listStyle: 'none', display: 'flex', gap: '30px', alignItems: 'center', margin: 0}}>
                <li>
                  <Link 
                    to="/" 
                    style={{textDecoration: 'none', color: '#666', fontWeight: 500, transition: 'color 0.3s ease'}}
                    onMouseOver={(e) => e.target.style.color = '#0277bd'}
                    onMouseOut={(e) => e.target.style.color = '#666'}
                  >
                    Products
                  </Link>
                </li>
                <li>
                  <a 
                    href="#" 
                    style={{textDecoration: 'none', color: '#666', fontWeight: 500, transition: 'color 0.3s ease'}}
                    onMouseOver={(e) => e.target.style.color = '#0277bd'}
                    onMouseOut={(e) => e.target.style.color = '#666'}
                  >
                    Contact Us
                  </a>
                </li>
                <li>
                  <a 
                    href="#" 
                    style={{textDecoration: 'none', color: '#666', fontWeight: 500, transition: 'color 0.3s ease'}}
                    onMouseOver={(e) => e.target.style.color = '#0277bd'}
                    onMouseOut={(e) => e.target.style.color = '#666'}
                  >
                    About Us
                  </a>
                </li>
                {user ? (
                  <>
                    <li>
                      <button 
                        className="signin-btn" 
                        onClick={() => navigate('/chat')}
                      >
                        Go to Chat
                      </button>
                    </li>
                    <li>
                      <button 
                        className="signup-btn" 
                        onClick={logout}
                      >
                        Logout
                      </button>
                    </li>
                  </>
                ) : (
                  <>
                    <li><button className="signin-btn" onClick={() => navigate('/login')}>Sign In</button></li>
                    <li><button className="signup-btn" onClick={() => navigate('/signup')}>Sign Up</button></li>
                  </>
                )}
              </ul>
            </nav>
          </div>
        </div>
      </header>

      <main>
        <div className="container">
          <section className="hero-section">
            <div className="hero-content">
              <h1>Start your journey by one click, explore beautiful Sri Lanka!</h1>
              <p>Experience the pearl of the Indian Ocean with exclusive deals, expert guidance, and unforgettable memories. Book now and save up to 40% on your dream vacation!</p>
              <button 
                className="cta-button" 
                onClick={() => user ? navigate('/chat') : navigate('/signup')}
              >
                {user ? 'Start Planning Your Trip!' : 'Start Your Adventure - Free Trial!'}
              </button>
            </div>
            <div className="hero-images">
              <img src="https://media.istockphoto.com/id/2158988664/photo/aerial-view-of-famous-beach-of-the-south-coast-of-sri-lanka-area-near-the-town-of-weligama.webp?a=1&b=1&s=612x612&w=0&k=20&c=oezERUpPMW7Tt_TG-o0o1MS3B2si9YJqkcg9N3OLEXg=" className="hero-main-img" alt="Sri Lanka Beach" />
              <div className="floating-badge badge1">🎯 40% OFF Limited Time!</div>
              <div className="floating-badge badge2">✨ 10K+ Happy Travelers</div>
            </div>
          </section>

          <section className="destinations">
            <h2 className="section-title">Popular Destinations</h2>
            <p className="section-subtitle">Discover Sri Lanka's most breathtaking locations with our expert-curated travel packages</p>
            <div className="destinations-grid">
              <div className="destination-card">
                <img src="https://images.unsplash.com/photo-1711797750174-c3750dd9d7c9?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8c2lnaXJpeWF8ZW58MHx8MHx8fDA%3D" alt="Sigiriya Rock" />
                <div className="card-content">
                  <h3>Sigiriya Rock Fortress</h3>
                  <p>Ancient wonder with panoramic views. Climb the legendary Lion Rock and discover 5th-century frescoes in this UNESCO World Heritage site.</p>
                </div>
              </div>
              <div className="destination-card">
                <img src="https://images.unsplash.com/photo-1642095012223-65ee6d570974?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTh8fHNyaSUyMGxhbmthJTIwdG91cmlzbXxlbnwwfHwwfHx8MA%3D%3D" alt="Temple of Tooth" />
                <div className="card-content">
                  <h3>Temple of the Sacred Tooth</h3>
                  <p>Sacred Buddhist temple in Kandy housing a tooth relic of Buddha. Experience spiritual tranquility in this magnificent cultural landmark.</p>
                </div>
              </div>
              <div className="destination-card">
                <img src="https://media.istockphoto.com/id/2164077307/photo/aerial-view-of-tea-plantation-near-the-lake-on-sri-lanka.webp?a=1&b=1&s=612x612&w=0&k=20&c=8rZIaABFAapYfd1Jng5ZipZLB1__DS199LRayqI9SKg=" alt="Tea plantations" />
                <div className="card-content">
                  <h3>Nuwara Eliya Tea Country</h3>
                  <p>Rolling green hills and colonial charm. Experience the cool climate, tea plantations, and scenic train rides through misty mountains.</p>
                </div>
              </div>
              <div className="destination-card">
                <img src="https://media.istockphoto.com/id/1254219156/photo/sunrise-over-galle-dutch-fort-lighthouse-surrounded-by-coconut-trees-in-sri-lanka.webp?a=1&b=1&s=612x612&w=0&k=20&c=bYJZasnNl4ixnOecseYOulTJgHvrfyoW6ZhbhGRcfFM=" alt="Galle Fort" />
                <div className="card-content">
                  <h3>Galle Dutch Fort</h3>
                  <p>Historic coastal fortress with cobblestone streets. Explore 400-year-old ramparts, boutique shops, and stunning ocean views.</p>
                </div>
              </div>
            </div>
          </section>

          <section className="why-choose-us">
            <div className="why-image">
              <img src="https://media.istockphoto.com/id/2157291795/photo/happy-tourist-couple-taking-selfie-while-exploring-the-city.jpg?s=612x612&w=0&k=20&c=UNZ-TTcpY7ThX8KfCGxrhkc5dxSTVtYm2S8IjpGqXIA=" alt="Travelers" />
            </div>

            <div className="why-content">
              <h2>Why Choose Us</h2>
              <p className="intro">
                Enjoy different experiences in every place you visit and discover new and affordable adventures of course.
              </p>

              <div className="features">
                <div className="feature-card">
                  <div className="icon">🧠</div>
                  <div className="text">
                    <h3>AI-Powered Personalization</h3>
                    <p>We use advanced AI to understand your preferences and recommend destinations, activities, and packages tailored just for you.</p>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="icon">☀️❄️🌧️</div>
                  <div className="text">
                    <h3>Season-Aware Suggestions</h3>
                    <p>Get recommendations based on real-time seasonal trends, weather, and local events — ensuring the best timing for your trip.</p>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="icon">🤖</div>
                  <div className="text">
                    <h3>All-in-One Smart Agents</h3>
                    <p>Conversation, location, activity, and packaging agents work together for a seamless travel planning experience.</p>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="icon">💰⏱️</div>
                  <div className="text">
                    <h3>Cost & Time Optimization</h3>
                    <p>We build optimized travel packages balancing budget, experience, and convenience better than traditional booking sites.</p>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="icon">🛡️</div>
                  <div className="text">
                    <h3>Trust, Safety & Responsible AI</h3>
                    <p>Your data is secure, recommendations are transparent, and our system is built on fairness and responsible AI principles.</p>
                  </div>
                </div>

                <div className="feature-card">
                  <div className="icon">🚀</div>
                  <div className="text">
                    <h3>Continuous Learning & Improvement</h3>
                    <p>The more you use it, the smarter it gets — adapting to your evolving travel style through feedback and learning.</p>
                  </div>
                </div>
              </div>

              <a href="#" className="more-link">Another Product →</a>
            </div>
          </section>
        </div>
      </main>

      {/* Chat Widget */}
      <div className="chat-widget">
        <button className="chat-button" onClick={toggleChat}>💬</button>
        {isChatOpen && (
          <div className="chat-window">
            <div className="chat-header">
              <h3>🤖 Travling AI Assistant</h3>
              <p>Hi! I'm here to help plan your Sri Lankan adventure!</p>
            </div>
            <div className="chat-messages">
              {chatMessages.map((message, index) => (
                <div key={index} className={`message ${message.type}-message`}>
                  {message.content.split('\n').map((line, lineIndex) => (
                    <React.Fragment key={lineIndex}>
                      {line}
                      {lineIndex < message.content.split('\n').length - 1 && <br />}
                    </React.Fragment>
                  ))}
                </div>
              ))}
            </div>
            <div className="chat-input">
              <input 
                type="text" 
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={handleChatKeyPress}
                placeholder="Ask me anything about travel..."
              />
              <button onClick={sendMessage}>➤</button>
            </div>
          </div>
        )}
      </div>

      {/* Sign In Modal */}
      {isSignInOpen && (
        <div className="modal" onClick={() => closeModal('signin')}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal" onClick={() => closeModal('signin')}>×</button>
            <h2>Welcome Back!</h2>
            {signInError && (
              <div style={{
                background: '#fee2e2',
                color: '#dc2626',
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '20px',
                fontSize: '14px'
              }}>
                {signInError}
              </div>
            )}
            <form onSubmit={handleSignIn}>
              <div className="form-group">
                <label>Email or Username</label>
                <input 
                  type="text" 
                  placeholder="Enter your email or username"
                  value={signInData.login}
                  onChange={(e) => setSignInData({...signInData, login: e.target.value})}
                  required
                  disabled={isSignInLoading}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input 
                  type="password" 
                  placeholder="Enter your password"
                  value={signInData.password}
                  onChange={(e) => setSignInData({...signInData, password: e.target.value})}
                  required
                  disabled={isSignInLoading}
                />
              </div>
              <button 
                type="submit" 
                className="signup-btn" 
                style={{width: '100%', marginTop: '10px'}}
                disabled={isSignInLoading}
              >
                {isSignInLoading ? 'Signing In...' : 'Sign In'}
              </button>
            </form>
            <p style={{marginTop: '20px', color: '#666'}}>
              Don't have an account? 
              <a href="#" onClick={(e) => {e.preventDefault(); switchModal('signin', 'signup');}} style={{color: '#0277bd'}}> Sign up here</a>
            </p>
          </div>
        </div>
      )}

      {/* Sign Up Modal */}
      {isSignUpOpen && (
        <div className="modal" onClick={() => closeModal('signup')}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal" onClick={() => closeModal('signup')}>×</button>
            <h2>Join Travling Today!</h2>
            <p style={{color: '#666', marginBottom: '20px'}}>🎁 Get 500 bonus points + 20% off your first booking!</p>
            {signUpError && (
              <div style={{
                background: '#fee2e2',
                color: '#dc2626',
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '20px',
                fontSize: '14px'
              }}>
                {signUpError}
              </div>
            )}
            <form onSubmit={handleSignUp}>
              <div className="form-group">
                <label>Username</label>
                <input 
                  type="text" 
                  placeholder="Choose a username"
                  value={signUpData.username}
                  onChange={(e) => setSignUpData({...signUpData, username: e.target.value})}
                  required
                  disabled={isSignUpLoading}
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input 
                  type="text" 
                  placeholder="Enter your full name"
                  value={signUpData.name}
                  onChange={(e) => setSignUpData({...signUpData, name: e.target.value})}
                  required
                  disabled={isSignUpLoading}
                />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input 
                  type="email" 
                  placeholder="Enter your email"
                  value={signUpData.email}
                  onChange={(e) => setSignUpData({...signUpData, email: e.target.value})}
                  required
                  disabled={isSignUpLoading}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input 
                  type="password" 
                  placeholder="Create a password"
                  value={signUpData.password}
                  onChange={(e) => setSignUpData({...signUpData, password: e.target.value})}
                  required
                  disabled={isSignUpLoading}
                  minLength={6}
                />
              </div>
              <button 
                type="submit" 
                className="signup-btn" 
                style={{width: '100%', marginTop: '10px'}}
                disabled={isSignUpLoading}
              >
                {isSignUpLoading ? 'Creating Account...' : 'Start Free Trial'}
              </button>
            </form>
            <p style={{marginTop: '20px', color: '#666'}}>
              Already have an account? 
              <a href="#" onClick={(e) => {e.preventDefault(); switchModal('signup', 'signin');}} style={{color: '#0277bd'}}> Sign in here</a>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;