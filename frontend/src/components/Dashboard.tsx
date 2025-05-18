import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Dashboard.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface Listing {
  id: string;
  title: string;
  price: string;
  location: string;
  date: string;
  link: string;
  image_url: string | null;
  scraped_at: string;
  is_new: boolean;
  seen: boolean;
}

const Dashboard: React.FC = () => {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showOnlyUnseen, setShowOnlyUnseen] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [retryCount, setRetryCount] = useState(0);
  const [stats, setStats] = useState({
    total: 0,
    unseen: 0
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const fetchListings = async () => {
    if (!token) {
      setError('Authentication token is missing');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      console.log('Fetching listings...');
      
      const response = await axios.get(`${API_URL}/listings?include_seen=${!showOnlyUnseen}`, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        withCredentials: true,
        timeout: 10000
      });
      
      console.log('Listings response:', response.data);
      
      if (Array.isArray(response.data)) {
        const validListings = response.data.filter((listing: any) => {
          return (
            typeof listing === 'object' &&
            typeof listing.id === 'string' &&
            typeof listing.title === 'string' &&
            typeof listing.price === 'string' &&
            typeof listing.location === 'string' &&
            typeof listing.link === 'string'
          );
        });
        
        console.log('Valid listings:', validListings);
        setListings(validListings);
        setStats({
          total: validListings.length,
          unseen: validListings.filter((l: Listing) => !l.seen).length
        });
        setRetryCount(0); // Reset retry count on success
      } else {
        console.error('Invalid response format:', response.data);
        setError('Invalid response format from server');
      }
    } catch (err) {
      console.error('Failed to fetch listings:', err);
      if (axios.isAxiosError(err)) {
        console.error('Error details:', {
          status: err.response?.status,
          data: err.response?.data,
          headers: err.response?.headers
        });
        
        if (err.response?.status === 401) {
          setError('Session expired. Please login again.');
        } else if (err.code === 'ERR_NETWORK') {
          setError('Network error. Please check if the server is running.');
        } else if (err.response?.status === 500) {
          setError(`Server error: ${err.response?.data?.detail || 'Unknown error'}`);
        } else {
          setError(`Failed to fetch listings: ${err.response?.data?.detail || err.message}`);
        }
      } else {
        setError('Failed to fetch listings. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    fetchListings();
  };

  const scrapeListings = async () => {
    try {
      setScraping(true);
      const response = await axios.post(`${API_URL}/scrape`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats({
        total: response.data.total_listings,
        unseen: response.data.unseen_listings
      });
      await fetchListings();
    } catch (err) {
      console.error('Failed to scrape listings:', err);
      if (axios.isAxiosError(err)) {
        if (err.response?.status === 401) {
          setError('Session expired. Please login again.');
        } else {
          setError(`Failed to scrape listings: ${err.response?.data?.detail || err.message}`);
        }
      } else {
        setError('Failed to scrape listings. Please try again.');
      }
    } finally {
      setScraping(false);
    }
  };

  const markAsSeen = async (listingIds: string[]) => {
    try {
      await axios.post(`${API_URL}/listings/mark-seen`, listingIds, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await fetchListings();
    } catch (err) {
      console.error('Failed to mark listings as seen:', err);
      if (axios.isAxiosError(err)) {
        if (err.response?.status === 401) {
          setError('Session expired. Please login again.');
        } else {
          setError(`Failed to mark listings as seen: ${err.response?.data?.detail || err.message}`);
        }
      } else {
        setError('Failed to mark listings as seen. Please try again.');
      }
    }
  };

  const exportListings = async (format: 'csv' | 'excel') => {
    try {
      await axios.post(`${API_URL}/listings/export?format=${format}&include_seen=${!showOnlyUnseen}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert(`Listings exported to ${format.toUpperCase()}`);
    } catch (err) {
      console.error('Failed to export listings:', err);
      if (axios.isAxiosError(err)) {
        if (err.response?.status === 401) {
          setError('Session expired. Please login again.');
        } else {
          setError(`Failed to export listings: ${err.response?.data?.detail || err.message}`);
        }
      } else {
        setError('Failed to export listings. Please try again.');
      }
    }
  };

  // Filter and sort listings
  const filteredAndSortedListings = useMemo(() => {
    console.log('Current listings:', listings);
    const filtered = listings
      .filter(listing => {
        const searchLower = searchQuery.toLowerCase();
        return (
          listing.title.toLowerCase().includes(searchLower) ||
          listing.location.toLowerCase().includes(searchLower) ||
          listing.price.toLowerCase().includes(searchLower)
        );
      })
      .sort((a, b) => new Date(b.scraped_at).getTime() - new Date(a.scraped_at).getTime());
    console.log('Filtered and sorted listings:', filtered);
    return filtered;
  }, [listings, searchQuery]);

  useEffect(() => {
    console.log('Dashboard mounted, token:', token ? 'present' : 'missing');
    fetchListings();
  }, [showOnlyUnseen]);

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner"></div>
        <p>Loading listings...</p>
      </div>
    );
  }

  if (!token) {
    return <div className="error">Please log in to view listings</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>OLX Listings</h1>
        <div className="dashboard-actions">
          <button 
            onClick={scrapeListings} 
            disabled={scraping}
            className="scrape-button"
          >
            {scraping ? 'Scraping...' : 'Scrape New Listings'}
          </button>
          <button onClick={() => exportListings('csv')} className="export-button">
            Export to CSV
          </button>
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        </div>
      </div>

      <div className="dashboard-stats">
        <div className="stat">
          <span className="stat-label">Total Listings:</span>
          <span className="stat-value">{stats.total}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Unseen Listings:</span>
          <span className="stat-value">{stats.unseen}</span>
        </div>
      </div>

      <div className="dashboard-filters">
        <div className="search-container">
          <input
            type="text"
            placeholder="Search by title, location, or price..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>
        <label className="unseen-filter">
          <input
            type="checkbox"
            checked={showOnlyUnseen}
            onChange={(e) => setShowOnlyUnseen(e.target.checked)}
          />
          Show only unseen listings
        </label>
      </div>

      {error && (
        <div className="error-container">
          <div className="error">{error}</div>
          <button onClick={handleRetry} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {filteredAndSortedListings.length === 0 ? (
        <div className="no-listings">
          {searchQuery ? 'No listings match your search' : 'No listings found'}
        </div>
      ) : (
        <div className="listings-grid">
          {filteredAndSortedListings.map((listing, index) => (
            <div 
              key={`${listing.id}-${index}`} 
              className={`listing-card ${listing.seen ? '' : 'unseen'}`}
            >
              <div className="listing-image">
                {listing.image_url ? (
                  <img 
                    src={listing.image_url} 
                    alt={listing.title}
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.onerror = null;
                      target.src = 'https://via.placeholder.com/300x200?text=No+Image';
                    }}
                  />
                ) : (
                  <div className="no-image">No Image</div>
                )}
              </div>
              <div className="listing-content">
                <h3 className="listing-title">
                  <a href={listing.link} target="_blank" rel="noopener noreferrer">
                    {listing.title}
                  </a>
                </h3>
                <p className="listing-price">{listing.price}</p>
                <p className="listing-location">{listing.location}</p>
                <p className="listing-date">
                  {new Date(listing.scraped_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                  })}
                </p>
                {!listing.seen && (
                  <button
                    onClick={() => markAsSeen([listing.id])}
                    className="mark-seen-button"
                  >
                    Mark as Seen
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard; 