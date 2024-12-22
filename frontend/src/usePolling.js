// usePolling.js
import { useState, useEffect } from 'react';

const usePolling = (url, interval) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        setError('Failed to fetch data: ' + err.message);
      }
    };

    fetchData();
    const pollingInterval = setInterval(fetchData, interval);

    return () => clearInterval(pollingInterval);
  }, [url, interval]);

  return { data, error };
};

export default usePolling;