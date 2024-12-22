import React, { useEffect, useRef } from 'react';

const LogComponent = ({ messages }) => {
  const endOfMessagesRef = useRef(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="text-white p-4 font-mono h-full overflow-auto text-sm">
      {messages.map((message, index) => (
        <div key={index} className="text-left mb-1">
          {message}
        </div>
      ))}
      <div ref={endOfMessagesRef} />
    </div>
  );
};

export default LogComponent;
