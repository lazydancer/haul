import React from 'react';

const InfoDisplay = ({ data }) => {

    // Convert profit rate from isk/s to isk/hr, round, and format
    const profitRatePerHour = Math.round(data.profit_rate * 3600).toLocaleString('en-US');

    // Format risk as percent and calculate risk cost, then round
    const riskPercent = (Math.round(data.risk * 100 * 100) / 100).toFixed(2) + '%';
    const riskCost = Math.round(data.risk * data.capital).toLocaleString('en-US');

    // Format capital
    const capitalFormatted = Math.round(data.capital).toLocaleString('en-US');

    // Convert transport time to minutes and seconds, then round
    const minutes = Math.floor(data.transport_time / 60);
    const seconds = Math.round(data.transport_time % 60);
    const transportTimeFormatted = `${minutes}m ${seconds}s`;

    // Format and round gross profit
    const grossProfitFormatted = Math.round(data.gross_profit).toLocaleString('en-US');

    const netProfitFormatted = Math.round(data.net_profit).toLocaleString('en-US');

    return (
        <div className="overall-data p-6 mt-4">
            <h2> </h2>
            <table style={{ width: '100%', textAlign: 'right' }}>
                <tbody>
                    <tr>
                        <td style={{ textAlign: 'left' }}>Profit Rate:</td>
                        <td>{profitRatePerHour} isk/hr</td>
                    </tr>
                    <tr>
                        <td style={{ textAlign: 'left' }}>Risk:</td>
                        <td>{riskPercent} ({riskCost} isk)</td>
                    </tr>
                    <tr>
                        <td style={{ textAlign: 'left' }}>Capital:</td>
                        <td>{capitalFormatted} isk</td>
                    </tr>
                    <tr>
                        <td style={{ textAlign: 'left' }}>Transport Time:</td>
                        <td>{transportTimeFormatted}</td>
                    </tr>
                    <tr>
                        <td style={{ textAlign: 'left' }}>Gross Profit:</td>
                        <td>{grossProfitFormatted} isk</td>
                    </tr>

                    <tr>
                        <td style={{ textAlign: 'left' }}>Net Profit:</td>
                        <td>{netProfitFormatted} isk</td>
                    </tr>
                </tbody>
            </table>
        </div>
    );
}

export default InfoDisplay;
