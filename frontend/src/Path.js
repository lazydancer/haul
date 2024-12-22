import React from 'react';
import usePolling from './usePolling';
import DataDisplay from './DataDisplay'; // Import the DataDisplay component

const Path = () => {
  const { data, error } = usePolling('http://localhost:8000/route', 1000);

  return (
    <div className="text-white">
      {error && <p>Error: {error}</p>}
      {data ? <DataDisplay data={data} /> : <p>Loading data...</p>}
    </div>
  );
};

export default Path;