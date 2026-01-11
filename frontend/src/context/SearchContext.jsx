import { createContext, useContext, useState } from 'react';

const SearchContext = createContext();

export function useSearch() {
    return useContext(SearchContext);
}

export function SearchProvider({ children }) {
    const [searchTerm, setSearchTerm] = useState('');
    const [filters, setFilters] = useState({
        sortBy: 'date-desc',
        fileTypes: [],
        dateFrom: '',
        dateTo: ''
    });

    const value = {
        searchTerm,
        setSearchTerm,
        filters,
        setFilters
    };

    return (
        <SearchContext.Provider value={value}>
            {children}
        </SearchContext.Provider>
    );
}
