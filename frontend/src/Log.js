import React from 'react';
import useSSE from './useSSE';
import LogComponent from './LogComponent'; // Import the DataDisplay component

const Log = () => {
    const { data, error } = useSSE('http://localhost:8000/data_stream', 2000);
  
    console.log("Log Data: ", data);

    return (
      <div className="text-white">
        {error && <p>Error: {error}</p>}
        {data ? <LogComponent messages={data.log} /> : <p>Loading data...</p>}
      </div>
    );
  };

export default Log;