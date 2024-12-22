import React from 'react';
import usePolling from './usePolling';
import InfoDisplay from './InfoDisplay'; // Import the DataDisplay component

const Info = () => {
    const { data, error } = usePolling('http://localhost:8000/route_info', 1000);
  
    return (
      <div className="text-white">
        {error && <p>Error: {error}</p>}
        {data ? <InfoDisplay data={data} /> : <p>Loading data...</p>}
      </div>
    );
  };

export default Info;