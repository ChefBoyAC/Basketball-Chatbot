import React from 'react';
import QueryForm from "./QueryForm";
import './page.css'; 

export default function Home() {
  return (
    <div className='chatbot'> 
        <h1>Basketball Chatbot🏀⛹🏾</h1>
        <QueryForm/>
    </div>
  );
}
