import React, { useState } from 'react';
import './Options.css';

const Options = () => {
  const [message, setMessage] = useState('');

  const handleClick = async () => {
    setMessage('Sending request...');
    try {
      const response = await fetch('http://localhost:8000/create_route', { method: 'POST' });
      const data = await response.json();
      setMessage(`Response received: ${JSON.stringify(data)}`);
    } catch (error) {
      setMessage(`Error: ${error}`);
    }
  };

  return (
    <div className="p-8">
      <button 
        className="options-button"
        onClick={handleClick}
      >
        Create Route
      </button>
      <p className='text-white pt-2'>{message}</p>
    </div>
  );
}

export default Options;