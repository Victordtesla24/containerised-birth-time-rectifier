import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../components/common/Layout';

// Celestial Background component with parallax effect
const CelestialBackground = ({ scrollPosition }) => {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden bg-indigo-900">
      {/* Stars layer (furthest) */}
      <div 
        className="absolute inset-0 bg-repeat"
        style={{
          backgroundImage: 'url(/images/stars-bg.png)',
          backgroundSize: '400px',
          transform: `translateY(${scrollPosition * 0.1}px)`
        }}
      ></div>
      
      {/* Nebula layer (middle) */}
      <div 
        className="absolute inset-0 bg-no-repeat bg-cover opacity-40"
        style={{
          backgroundImage: 'url(/images/nebula-bg.png)',
          backgroundPosition: 'center',
          transform: `translateY(${scrollPosition * 0.2}px)`
        }}
      ></div>
      
      {/* Galaxies layer (closest) */}
      <div 
        className="absolute inset-0 bg-no-repeat bg-cover opacity-20"
        style={{
          backgroundImage: 'url(/images/galaxies-bg.png)',
          backgroundPosition: '75% 50%',
          transform: `translateY(${scrollPosition * 0.3}px)`
        }}
      ></div>
      
      {/* Gradient overlay to improve text readability */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-indigo-900 opacity-80"></div>
    </div>
  );
};

// Feature section component
const Feature = ({ icon, title, description }) => (
  <div className="feature p-6 bg-indigo-800 bg-opacity-40 rounded-lg border border-indigo-400 border-opacity-20 transition-all duration-300 hover:bg-opacity-50 hover:shadow-lg">
    <div className="text-2xl text-indigo-300 mb-4">{icon}</div>
    <h3 className="text-xl font-medium text-white mb-2">{title}</h3>
    <p className="text-indigo-200">{description}</p>
  </div>
);

// Testimonial component
const Testimonial = ({ quote, author, role }) => (
  <div className="testimonial p-6 bg-indigo-900 bg-opacity-40 rounded-lg border border-indigo-400 border-opacity-10">
    <p className="text-indigo-100 italic mb-4">"{quote}"</p>
    <div className="flex items-center">
      <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center mr-3">
        <span className="text-white font-bold">{author.charAt(0)}</span>
      </div>
      <div>
        <div className="text-white font-medium">{author}</div>
        <div className="text-indigo-300 text-sm">{role}</div>
      </div>
    </div>
  </div>
);

export default function Home() {
  const [scrollPosition, setScrollPosition] = useState(0);
  
  // Handle scroll for parallax effect
  useEffect(() => {
    const handleScroll = () => {
      setScrollPosition(window.pageYOffset);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);
  
  const features = [
    {
      icon: '✨',
      title: 'AI-Powered Analysis',
      description: 'Our advanced AI algorithms analyze your birth details and life events to determine your most accurate birth time.'
    },
    {
      icon: '🌙',
      title: 'Vedic Astrology',
      description: 'Full support for traditional Vedic astrology principles, with North Indian style charts and planetary positions.'
    },
    {
      icon: '⏱️',
      title: 'High Precision',
      description: 'Rectify your birth time with high precision through our adaptive questionnaire that refines results with each answer.'
    },
    {
      icon: '📊',
      title: 'Interactive Charts',
      description: 'Visualize your birth chart in the traditional North Indian style with clear house and planet placements.'
    },
    {
      icon: '🔮',
      title: 'Detailed Interpretation',
      description: 'Understand the significance of your rectified birth time and how it impacts your astrological profile.'
    },
    {
      icon: '🧠',
      title: 'Tailored Questions',
      description: 'Our AI generates personalized questions based on your chart to improve rectification accuracy.'
    }
  ];
  
  const testimonials = [
    {
      quote: "I never knew my exact birth time, and this tool helped me nail it down with amazing accuracy. The personalized questions were spot on!",
      author: "Priya S.",
      role: "Yoga Instructor"
    },
    {
      quote: "As an astrologer, I recommend this tool to all my clients with uncertain birth times. The AI algorithms are incredibly precise.",
      author: "Michael T.",
      role: "Professional Astrologer"
    },
    {
      quote: "The North Indian chart visualization is beautiful and accurate. This is the best birth time rectification tool I've found.",
      author: "Lisa R.",
      role: "Astrology Enthusiast"
    }
  ];

  return (
    <Layout>
      <CelestialBackground scrollPosition={scrollPosition} />
      
      <div className="container mx-auto px-4 py-12 max-w-6xl relative z-10">
        {/* Hero Section */}
        <div className="hero text-center mb-20">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            AI-Powered Birth Time<br/>Rectification
          </h1>
          <p className="text-xl text-indigo-200 mb-10 max-w-3xl mx-auto">
            Discover your precise birth time using our advanced AI and Vedic astrological principles for more accurate chart readings.
          </p>
          <Link href="/birth-details">
            <div className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-4 px-8 rounded-lg transition duration-200 text-lg">
              Start Your Analysis
            </div>
          </Link>
        </div>
        
        {/* How It Works Section */}
        <div className="how-it-works mb-20">
          <h2 className="text-3xl font-bold text-white text-center mb-12">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="step text-center p-6">
              <div className="step-number bg-indigo-600 text-white w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">1</div>
              <h3 className="text-xl font-medium text-white mb-3">Enter Birth Details</h3>
              <p className="text-indigo-200">Provide your birth date, approximate time, and location information.</p>
            </div>
            <div className="step text-center p-6">
              <div className="step-number bg-indigo-600 text-white w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">2</div>
              <h3 className="text-xl font-medium text-white mb-3">Answer Questions</h3>
              <p className="text-indigo-200">Our AI will ask tailored questions based on your astrological profile.</p>
            </div>
            <div className="step text-center p-6">
              <div className="step-number bg-indigo-600 text-white w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">3</div>
              <h3 className="text-xl font-medium text-white mb-3">Get Results</h3>
              <p className="text-indigo-200">Receive your rectified birth time with detailed chart visualization.</p>
            </div>
          </div>
        </div>
        
        {/* Features Section */}
        <div className="features mb-20">
          <h2 className="text-3xl font-bold text-white text-center mb-12">Key Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Feature 
                key={index}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
              />
            ))}
          </div>
        </div>
        
        {/* Testimonials Section */}
        <div className="testimonials mb-20">
          <h2 className="text-3xl font-bold text-white text-center mb-12">User Testimonials</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <Testimonial 
                key={index}
                quote={testimonial.quote}
                author={testimonial.author}
                role={testimonial.role}
              />
            ))}
          </div>
        </div>
        
        {/* Call to Action */}
        <div className="cta text-center bg-indigo-800 bg-opacity-40 p-10 rounded-lg border border-indigo-400 border-opacity-20 mb-12">
          <h2 className="text-3xl font-bold text-white mb-6">Ready to Discover Your True Birth Time?</h2>
          <p className="text-indigo-200 mb-8 max-w-2xl mx-auto">
            Start the rectification process now to get more accurate astrological insights for your life path, personality, and future predictions.
          </p>
          <Link href="/birth-details">
            <div className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-8 rounded-lg transition duration-200">
              Begin Your Journey
            </div>
          </Link>
        </div>
        
        {/* Footer */}
        <div className="footer text-center text-indigo-300 text-sm">
          <p>Birth Time Rectifier © 2025 • AI-Powered Vedic Astrology</p>
          <p className="mt-2">Your data is processed securely and used exclusively for birth time rectification.</p>
        </div>
      </div>
    </Layout>
  );
} 