import logo from './logo.png';
import './App.css';

import Path from './Path';
import Log from './Log';
import Options from './Options';
import Info from './Info';

function App() {
  return (
    <div className="App flex flex-wrap h-screen">
      {/* Main component for Path */}
      <div className="w-2/3 h-full overflow-auto hide-scrollbar">
        <Path />
      </div>
      {/* Sidebar for Options, LogComponent, and Logo */}
      <div className="w-1/3 h-full flex flex-col">
        <div className="h-1/4 overflow-auto">
          <Info />
        </div>
        <div className="h-1/4 overflow-auto">
          <Options />
        </div>
        <div className="h-1/4 overflow-auto">
          <Log/>
        </div>
        <div className="h-1/4 flex items-center justify-center overflow-auto">
          <img src={logo} className="App-logo" alt="logo" />
        </div>
      </div>
    </div>
  );
}

export default App;
