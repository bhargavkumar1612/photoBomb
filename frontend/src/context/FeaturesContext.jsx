import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const FeaturesContext = createContext(null);

export const FeaturesProvider = ({ children }) => {
    const [features, setFeatures] = useState({
        animal_detection_enabled: false,
        face_recognition_enabled: true,
        loading: true
    });

    useEffect(() => {
        const fetchFeatures = async () => {
            try {
                const response = await api.get('/config/features');
                setFeatures({
                    ...response.data,
                    loading: false
                });
            } catch (error) {
                console.error('Failed to fetch features:', error);
                setFeatures(prev => ({ ...prev, loading: false }));
            }
        };

        fetchFeatures();
    }, []);

    return (
        <FeaturesContext.Provider value={features}>
            {children}
        </FeaturesContext.Provider>
    );
};

export const useFeatures = () => {
    const context = useContext(FeaturesContext);
    if (!context) {
        throw new Error('useFeatures must be used within FeaturesProvider');
    }
    return context;
};
