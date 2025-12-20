import React from 'react';

const HorizontalLoader = () => (
    <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        width: '100%',
        height: '100%',
        minHeight: '100px',
        background: '#f3f4f6'
    }}>
        <svg width="60" height="15" viewBox="0 0 60 15" xmlns="http://www.w3.org/2000/svg" fill="#3b82f6">
            <circle cx="7.5" cy="7.5" r="7.5">
                <animate attributeName="r" from="7.5" to="7.5" begin="0s" dur="0.8s" values="7.5;4;7.5" calcMode="linear" repeatCount="indefinite" />
                <animate attributeName="fill-opacity" from="1" to="1" begin="0s" dur="0.8s" values="1;.5;1" calcMode="linear" repeatCount="indefinite" />
            </circle>
            <circle cx="30" cy="7.5" r="7.5" fillOpacity="0.5">
                <animate attributeName="r" from="7.5" to="7.5" begin="0s" dur="0.8s" values="4;7.5;4" calcMode="linear" repeatCount="indefinite" />
                <animate attributeName="fill-opacity" from="0.5" to="0.5" begin="0s" dur="0.8s" values=".5;1;.5" calcMode="linear" repeatCount="indefinite" />
            </circle>
            <circle cx="52.5" cy="7.5" r="7.5">
                <animate attributeName="r" from="7.5" to="7.5" begin="0s" dur="0.8s" values="7.5;4;7.5" calcMode="linear" repeatCount="indefinite" />
                <animate attributeName="fill-opacity" from="1" to="1" begin="0s" dur="0.8s" values="1;.5;1" calcMode="linear" repeatCount="indefinite" />
            </circle>
        </svg>
    </div>
);

export default HorizontalLoader;
