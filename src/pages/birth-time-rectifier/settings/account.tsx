import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { CelestialBackground } from '@/components/visualization/CelestialBackground';

interface UserProfile {
  name: string;
  email: string;
  birthDate: string;
  birthTime: string;
  birthPlace: string;
  timezone: string;
  subscriptionTier: 'free' | 'standard' | 'premium';
  subscriptionStatus: 'active' | 'expired' | 'canceled';
  subscriptionExpiry: string | null;
  usageStats: {
    rectificationsUsed: number;
    rectificationsLimit: number;
    exportCredits: number;
    shareCredits: number;
  };
}

export default function AccountPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile>({
    name: '',
    email: '',
    birthDate: '',
    birthTime: '',
    birthPlace: '',
    timezone: '',
    subscriptionTier: 'free',
    subscriptionStatus: 'active',
    subscriptionExpiry: null,
    usageStats: {
      rectificationsUsed: 0,
      rectificationsLimit: 3,
      exportCredits: 1,
      shareCredits: 1,
    },
  });
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editedProfile, setEditedProfile] = useState<UserProfile | null>(null);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load profile from localStorage when the component mounts
  useEffect(() => {
    try {
      const storedProfile = localStorage.getItem('userProfile');
      if (storedProfile) {
        setProfile(JSON.parse(storedProfile));
      } else {
        // For demo purposes, create a mock profile
        const demoProfile: UserProfile = {
          name: 'John Doe',
          email: 'john.doe@example.com',
          birthDate: '1990-01-15',
          birthTime: '14:30',
          birthPlace: 'New York, USA',
          timezone: 'America/New_York',
          subscriptionTier: 'standard',
          subscriptionStatus: 'active',
          subscriptionExpiry: '2023-12-31',
          usageStats: {
            rectificationsUsed: 5,
            rectificationsLimit: 10,
            exportCredits: 5,
            shareCredits: 10,
          },
        };
        setProfile(demoProfile);
        localStorage.setItem('userProfile', JSON.stringify(demoProfile));
      }
    } catch (err) {
      console.error('Error loading profile:', err);
    }
  }, []);

  const handleEditToggle = () => {
    if (isEditing) {
      setIsEditing(false);
      setEditedProfile(null);
    } else {
      setIsEditing(true);
      setEditedProfile({...profile});
    }
  };

  const handleInputChange = (field: keyof UserProfile, value: string) => {
    if (editedProfile) {
      setEditedProfile({
        ...editedProfile,
        [field]: value,
      });
    }
  };

  const handleSave = () => {
    if (!editedProfile) return;
    
    setIsSaving(true);
    try {
      // In a real app, you would make an API call here to update the profile
      // For this demo, we'll just update localStorage
      localStorage.setItem('userProfile', JSON.stringify(editedProfile));
      setProfile(editedProfile);
      setIsEditing(false);
      setEditedProfile(null);
      setSaveMessage({ type: 'success', text: 'Profile updated successfully!' });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      console.error('Error saving profile:', err);
      setSaveMessage({ type: 'error', text: 'Failed to update profile. Please try again.' });
    } finally {
      setIsSaving(false);
    }
  };

  const formatSubscriptionTier = (tier: string) => {
    return tier.charAt(0).toUpperCase() + tier.slice(1);
  };

  const upgradeSubscription = () => {
    // In a real app, this would redirect to a payment page
    alert('This would redirect to a payment page in a real application.');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Birth Time Rectifier | Account</title>
        <meta name="description" content="Manage your account settings" />
      </Head>

      <CelestialBackground />

      <main className="container mx-auto px-4 py-8 relative z-10">
        <h1 className="text-3xl font-bold text-center mb-8 text-white">
          Account Settings
        </h1>

        <div className="max-w-3xl mx-auto bg-white bg-opacity-90 backdrop-blur-sm rounded-lg shadow p-6">
          {/* Save Message */}
          {saveMessage && (
            <div className={`p-4 mb-6 rounded-md ${
              saveMessage.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {saveMessage.text}
            </div>
          )}

          {/* Profile Section */}
          <div className="mb-8">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Personal Information</h2>
              <button
                type="button"
                onClick={handleEditToggle}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-md hover:bg-blue-200"
              >
                {isEditing ? 'Cancel' : 'Edit'}
              </button>
            </div>

            {isEditing && editedProfile ? (
              <form onSubmit={(e) => { e.preventDefault(); handleSave(); }}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                    <input
                      type="text"
                      value={editedProfile.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      value={editedProfile.email}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Birth Date</label>
                    <input
                      type="date"
                      value={editedProfile.birthDate}
                      onChange={(e) => handleInputChange('birthDate', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Birth Time</label>
                    <input
                      type="time"
                      value={editedProfile.birthTime}
                      onChange={(e) => handleInputChange('birthTime', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Birth Place</label>
                    <input
                      type="text"
                      value={editedProfile.birthPlace}
                      onChange={(e) => handleInputChange('birthPlace', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                    <input
                      type="text"
                      value={editedProfile.timezone}
                      onChange={(e) => handleInputChange('timezone', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={isSaving}
                    className={`px-4 py-2 bg-blue-600 text-white rounded-md ${
                      isSaving ? 'opacity-70 cursor-not-allowed' : 'hover:bg-blue-700'
                    }`}
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Name</p>
                  <p className="font-medium">{profile.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Email</p>
                  <p className="font-medium">{profile.email}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Birth Date</p>
                  <p className="font-medium">{profile.birthDate}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Birth Time</p>
                  <p className="font-medium">{profile.birthTime}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Birth Place</p>
                  <p className="font-medium">{profile.birthPlace}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Timezone</p>
                  <p className="font-medium">{profile.timezone}</p>
                </div>
              </div>
            )}
          </div>

          {/* Subscription Section */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-4">Subscription</h2>
            <div className="bg-blue-50 p-4 rounded-md mb-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium text-blue-800">{formatSubscriptionTier(profile.subscriptionTier)} Plan</p>
                  <p className="text-sm text-blue-600">
                    Status: <span className="capitalize">{profile.subscriptionStatus}</span>
                  </p>
                  {profile.subscriptionExpiry && (
                    <p className="text-sm text-blue-600">
                      Expires: {profile.subscriptionExpiry}
                    </p>
                  )}
                </div>
                {profile.subscriptionTier !== 'premium' && (
                  <button
                    type="button"
                    onClick={upgradeSubscription}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Upgrade
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Usage Stats Section */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-4">Usage Statistics</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-green-50 p-4 rounded-md">
                <p className="text-sm text-green-600">Rectifications</p>
                <p className="font-medium text-green-800">
                  {profile.usageStats.rectificationsUsed} / {profile.usageStats.rectificationsLimit} used
                </p>
                <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
                  <div 
                    className="bg-green-600 h-2.5 rounded-full" 
                    style={{ width: `${(profile.usageStats.rectificationsUsed / profile.usageStats.rectificationsLimit) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div className="bg-purple-50 p-4 rounded-md">
                <p className="text-sm text-purple-600">Export Credits</p>
                <p className="font-medium text-purple-800">{profile.usageStats.exportCredits} credits available</p>
              </div>
              <div className="bg-yellow-50 p-4 rounded-md">
                <p className="text-sm text-yellow-600">Share Credits</p>
                <p className="font-medium text-yellow-800">{profile.usageStats.shareCredits} credits available</p>
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="flex justify-between">
            <button
              type="button"
              onClick={() => router.push('/birth-time-rectifier/analysis')}
              className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
            >
              Back to Analysis
            </button>
            <button
              type="button"
              onClick={() => router.push('/birth-time-rectifier/settings/preferences')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Chart Preferences
            </button>
          </div>
        </div>
      </main>
    </div>
  );
} 