import { useState, useEffect } from 'react';

const useSSE = (url) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const eventSource = new EventSource(url);

    eventSource.onmessage = e => {
      try {
        const result = JSON.parse(e.data);
        setData(result);
      } catch (err) {
        setError('Failed to parse data: ' + err.message);
      }
    };

    eventSource.onerror = e => {
      setError('EventSource failed');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [url]);

  return { data, error };
};

export default useSSE;
