import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './DataDisplay.css'; // Import the CSS file for transitions


const DataDisplay = ({ data }) => { 
    console.log("DataDisplay Data: ", data);  
    const getIcon = (name) => {
        // Replace these with actual icon components or image tags
        if (name === 'system') return <svg width="12" height="6" xmlns="http://www.w3.org/2000/svg">
                <circle cx="6" cy="3" r="3" fill="white" />
            </svg>;
        if (name === 'station') return <svg width="12" height="12" xmlns="http://www.w3.org/2000/svg">
                <rect x="1" y="1" width="10" height="10" rx="0" fill="white" />
            </svg>;
        if (name === 'buy') return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="#FFFFFF" className="w-5 h-5">
                <path fillRule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" clipRule="evenodd" />
            </svg>;
        if (name === 'sell') return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="#FFFFFF" className="w-5 h-5">
                <path fillRule="evenodd" d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z" clipRule="evenodd" />
            </svg>;     

        return ''; // Default icon or empty
    };
  
    if (!data) {
        return <p>Loading ...</p>
    }

    const handleItemClick = async (typeId) => {
        try {
            const response = await fetch(`http://localhost:8000/open_market_window/${typeId}`, { method: 'POST' });
            console.log('Server Response:', response.data);
            // Handle response or set state as needed
        } catch (error) {
            console.error('Error posting to server:', error);
            // Handle error
        }
    }


    const containerVariants = {
        hidden: { opacity: 0, y: -20 },
        visible: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -20 }
    };

    return (
    <div className="text-white p-6">
        <AnimatePresence>
        {data.map((location, index) => (
            <motion.div
            key={location.id}
            initial="hidden"
            animate="visible"
            exit="exit"
            variants={containerVariants}
            transition={{ duration: 0.5 }}
            layout
            className="mt-4 ml-6"
            >
            <div className="flex items-center">
                <span className="pr-4">
                    {getIcon(location.location_type)}
                </span>
                <h3 className={`${index === 0 ? 'font-semibold text-xl text-left' : 'text-left'}`}>{location.location}</h3>
            </div>
            <div>
                {location.actions.length > 0 ? (
                <div className="gridCustom">
                    {location.actions.map((action, actionIndex) => (
                    <React.Fragment key={actionIndex}>
                        <div>{getIcon(action.action_type)}</div>
                        <div onClick={() => handleItemClick(action.type_id)} className={`${index === 0 ? 'font-semibold' : ''}`} style={{ cursor: 'pointer' }}>{action.item}</div>
                        <div className={`${index === 0 ? 'font-semibold' : ''}`} style={{ textAlign: 'right' }}>{action.quantity}</div>
                        <div className={`${index === 0 ? 'font-semibold' : ''}`} style={{ textAlign: 'right' }}>{action.price ? `$${action.price.toLocaleString()}` : '-'}</div>
                    </React.Fragment>
                    ))}
                </div>
                ) : (
                <p className="text-gray-500"></p>
                )}
            </div>
            </motion.div>
        ))}
        </AnimatePresence>


    </div>
    );

  };
  
export default DataDisplay;