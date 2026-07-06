import { useState, useEffect } from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TableSortLabel,
    Paper,
    Select,
    MenuItem,
    Button,
    Box,
    Typography
} from "@mui/material";

/**
 * CompactAnalysisTable - Simplified table with filters and sorting in headers
 * Column order: Question (with timestamp), Report Type, Audience, Origin, Destination
 * Clicking a row selects the analysis (no separate View button)
 * Headers provide both sorting and filtering capabilities
 */
export default function CompactAnalysisTable({ analyses, onSelectAnalysis }) {
    const [filters, setFilters] = useState({
        question: "",
        document_type: "",
        audience: "",
        origin: "",
        destination: ""
    });

    const [filteredAnalyses, setFilteredAnalyses] = useState(analyses);
    const [sortConfig, setSortConfig] = useState({
        key: null,
        direction: 'asc'
    });

    // Update filtered analyses when analyses or filters change
    useEffect(() => {
        applyFilters();
    }, [analyses, filters]);

    useEffect(() => {
        applySorting();
    }, [filteredAnalyses, sortConfig]);

    const applyFilters = () => {
        const result = analyses.filter(analysis => {
            const metadata = analysis.metadata || {};
            const question = (analysis.question || '').toLowerCase();
            const filterQuestion = filters.question.toLowerCase();

            return (!filters.question || question.includes(filterQuestion)) &&
                (!filters.document_type || metadata.document_type === filters.document_type) &&
                (!filters.audience || metadata.audience === filters.audience) &&
                (!filters.origin || metadata.origin === filters.origin) &&
                (!filters.destination || metadata.destination === filters.destination);
        });
        setFilteredAnalyses(result);
    };

    const applySorting = () => {
        if (sortConfig.key) {
            setFilteredAnalyses(prev => [...prev].sort((a, b) => {
                const aValue = getSortValue(a, sortConfig.key);
                const bValue = getSortValue(b, sortConfig.key);
                
                if (aValue < bValue) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            }));
        }
    };

    const getSortValue = (analysis, key) => {
        const metadata = analysis.metadata || {};
        
        switch (key) {
            case 'question': return (analysis.question || '').toLowerCase();
            case 'document_type': return (metadata.document_type || '').toLowerCase();
            case 'audience': return (metadata.audience || '').toLowerCase();
            case 'origin': return (metadata.origin || '').toLowerCase();
            case 'destination': return (metadata.destination || '').toLowerCase();
            case 'timestamp': 
                const date = new Date(analysis.timestamp || metadata.generated_at);
                return date.getTime();
            default: return '';
        }
    };

    const requestSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const resetFilters = () => {
        setFilters({
            question: "",
            document_type: "",
            audience: "",
            origin: "",
            destination: ""
        });
    };

    // Extract unique values for filter dropdowns from metadata
    const getUniqueValues = (field) => {
        const values = new Set();
        analyses.forEach(analysis => {
            const metadata = analysis.metadata || {};
            if (metadata[field]) {
                values.add(metadata[field]);
            }
        });
        return Array.from(values).sort();
    };

    if (!analyses || analyses.length === 0) {
        return (
            <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
                <Typography variant="body1">No previous analyses found.</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ width: '100%' }}>
            <TableContainer component={Paper} sx={{ border: '1px solid #e0e0e0', boxShadow: 'none' }}>
                <Table aria-label="analyses table" size="small">
                    <TableHead>
                        <TableRow>
                            {/* Question Column - Sortable */}
                            <TableCell>
                                <TableSortLabel
                                    active={sortConfig.key === 'question'}
                                    direction={sortConfig.key === 'question' ? sortConfig.direction : 'asc'}
                                    onClick={() => requestSort('question')}
                                    sx={{ fontWeight: 'bold', fontSize: '0.85rem' }}
                                >
                                    Question
                                </TableSortLabel>
                            </TableCell>
                            
                            {/* Report Type Column - Filterable */}
                            <TableCell>
                                <Select
                                    value={filters.document_type}
                                    onChange={(e) => setFilters({ ...filters, document_type: e.target.value })}
                                    displayEmpty
                                    size="small"
                                    sx={{ minWidth: 120, fontSize: '0.85rem' }}
                                >
                                    <MenuItem value="">All Types</MenuItem>
                                    {getUniqueValues('document_type').map(type => (
                                        <MenuItem key={type} value={type}>{type}</MenuItem>
                                    ))}
                                </Select>
                            </TableCell>
                            
                            {/* Audience Column - Filterable */}
                            <TableCell>
                                <Select
                                    value={filters.audience}
                                    onChange={(e) => setFilters({ ...filters, audience: e.target.value })}
                                    displayEmpty
                                    size="small"
                                    sx={{ minWidth: 120, fontSize: '0.85rem' }}
                                >
                                    <MenuItem value="">All Audiences</MenuItem>
                                    {getUniqueValues('audience').map(audience => (
                                        <MenuItem key={audience} value={audience}>{audience}</MenuItem>
                                    ))}
                                </Select>
                            </TableCell>
                            
                            {/* Origin Column - Filterable */}
                            <TableCell>
                                <Select
                                    value={filters.origin}
                                    onChange={(e) => setFilters({ ...filters, origin: e.target.value })}
                                    displayEmpty
                                    size="small"
                                    sx={{ minWidth: 120, fontSize: '0.85rem' }}
                                >
                                    <MenuItem value="">All Origins</MenuItem>
                                    {getUniqueValues('origin').map(origin => (
                                        <MenuItem key={origin} value={origin}>{origin}</MenuItem>
                                    ))}
                                </Select>
                            </TableCell>
                            
                            {/* Destination Column - Filterable */}
                            <TableCell>
                                <Select
                                    value={filters.destination}
                                    onChange={(e) => setFilters({ ...filters, destination: e.target.value })}
                                    displayEmpty
                                    size="small"
                                    sx={{ minWidth: 120, fontSize: '0.85rem' }}
                                >
                                    <MenuItem value="">All Destinations</MenuItem>
                                    {getUniqueValues('destination').map(destination => (
                                        <MenuItem key={destination} value={destination}>{destination}</MenuItem>
                                    ))}
                                </Select>
                            </TableCell>
                            
                            {/* Reset Button */}
                            <TableCell>
                                <Button
                                    onClick={resetFilters}
                                    size="small"
                                    variant="outlined"
                                    sx={{ fontSize: '0.75rem', minWidth: 'auto' }}
                                >
                                    x Reset
                                </Button>
                            </TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredAnalyses.map((analysis) => {
                            const metadata = analysis.metadata || {};
                            const generatedAt = new Date(analysis.timestamp || metadata.generated_at).toLocaleString();
                            const question = analysis.question || metadata.question || '';

                            return (
                                <TableRow
                                    key={analysis.unique_id || analysis.id}
                                    hover
                                    sx={{ cursor: 'pointer' }}
                                    onClick={() => onSelectAnalysis(analysis)}
                                >
                                    {/* Question Cell with Timestamp */}
                                    <TableCell>
                                        <Box>
                                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                                {question}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">
                                                {generatedAt}
                                            </Typography>
                                        </Box>
                                    </TableCell>
                                    
                                    {/* Report Type Cell */}
                                    <TableCell>{metadata.document_type || ''}</TableCell>
                                    
                                    {/* Audience Cell */}
                                    <TableCell>{metadata.audience || ''}</TableCell>
                                    
                                    {/* Origin Cell */}
                                    <TableCell>{metadata.origin || ''}</TableCell>
                                    
                                    {/* Destination Cell */}
                                    <TableCell>{metadata.destination || ''}</TableCell>
                                    
                                    {/* Empty cell for spacing */}
                                    <TableCell></TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>

            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                <Typography variant="body2" color="text.secondary">
                    Showing {filteredAnalyses.length} of {analyses.length} analyses
                    {filters.question || filters.document_type || filters.audience ||
                        filters.origin || filters.destination ?
                        <span style={{ backgroundColor: '#0072BC', color: 'white', 
                                     padding: '2px 6px', borderRadius: '4px', marginLeft: '8px', fontSize: '0.75rem' }}>
                            (filtered)
                        </span> : null}
                </Typography>
            </Box>
        </Box>
    );
}