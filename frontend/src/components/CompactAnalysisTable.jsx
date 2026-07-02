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
 * CompactAnalysisTable - Simplified table with filters in header using Material-UI
 * More compact design with direct links instead of view buttons
 */
export default function CompactAnalysisTable({ analyses, onSelectAnalysis }) {
    const [filters, setFilters] = useState({
        audience: "",
        document_type: "",
        origin: "",
        destination: "",
        timespan: ""
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

            return (!filters.audience || metadata.audience === filters.audience) &&
                (!filters.document_type || metadata.document_type === filters.document_type) &&
                (!filters.origin || metadata.origin === filters.origin) &&
                (!filters.destination || metadata.destination === filters.destination) &&
                (!filters.timespan || metadata.timespan === filters.timespan);
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
            case 'question': return analysis.question || '';
            case 'document_type': return metadata.document_type || '';
            case 'origin': return metadata.origin || '';
            case 'destination': return metadata.destination || '';
            case 'timespan': return metadata.timespan || '';
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
            audience: "",
            document_type: "",
            origin: "",
            destination: "",
            timespan: ""
        });
    };

    // Extract unique values for filter dropdowns
    const getUniqueValues = (field) => {
        const values = new Set();
        analyses.forEach(analysis => {
            if (analysis.metadata?.[field]) {
                values.add(analysis.metadata[field]);
            }
        });
        return Array.from(values);
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
                            <TableCell>
                                <TableSortLabel
                                    active={sortConfig.key === 'destination'}
                                    direction={sortConfig.key === 'destination' ? sortConfig.direction : 'asc'}
                                    onClick={() => requestSort('destination')}
                                    sx={{ fontWeight: 'bold', fontSize: '0.85rem' }}
                                >
                                    Destination
                                </TableSortLabel>
                            </TableCell>
                            <TableCell>
                                <Select
                                    value={filters.timespan}
                                    onChange={(e) => setFilters({ ...filters, timespan: e.target.value })}
                                    displayEmpty
                                    size="small"
                                    sx={{ minWidth: 120, fontSize: '0.85rem' }}
                                >
                                    <MenuItem value="">All Timespans</MenuItem>
                                    {getUniqueValues('timespan').map(timespan => (
                                        <MenuItem key={timespan} value={timespan}>{timespan}</MenuItem>
                                    ))}
                                </Select>
                            </TableCell>
                            <TableCell>
                                <TableSortLabel
                                    active={sortConfig.key === 'timestamp'}
                                    direction={sortConfig.key === 'timestamp' ? sortConfig.direction : 'asc'}
                                    onClick={() => requestSort('timestamp')}
                                    sx={{ fontWeight: 'bold', fontSize: '0.85rem' }}
                                >
                                    Date
                                </TableSortLabel>
                            </TableCell>
                            <TableCell>
                                <Button
                                    onClick={resetFilters}
                                    size="small"
                                    variant="outlined"
                                    sx={{ fontSize: '0.75rem', minWidth: 'auto' }}
                                >
                                    ✕ Reset
                                </Button>
                            </TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredAnalyses.map((analysis) => {
                            const metadata = analysis.metadata || {};
                            const generatedAt = new Date(analysis.timestamp || metadata.generated_at).toLocaleString();

                            return (
                                <TableRow
                                    key={analysis.unique_id || analysis.id}
                                    hover
                                    sx={{ cursor: 'pointer' }}
                                    onClick={() => onSelectAnalysis(analysis)}
                                >
                                    <TableCell>
                                        <Box>
                                            <Typography variant="body2" sx={{ fontWeight: 'medium', color: 'primary.main' }}>
                                                {metadata.audience || 'General'}
                                            </Typography>
                                        </Box>
                                    </TableCell>
                                    <TableCell>
                                        <Box>
                                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                                {analysis.question}
                                            </Typography>
                                            <Typography variant="caption" color="text.secondary">
                                                {metadata.analysis_type || 'unknown'}
                                            </Typography>
                                        </Box>
                                    </TableCell>
                                    <TableCell>{metadata.document_type || 'N/A'}</TableCell>
                                    <TableCell>
                                        {metadata.origin ? (
                                            <>
                                                <span style={{ fontWeight: 'medium' }}>{metadata.origin}</span>
                                                {metadata.destination && ' → '}
                                                <span style={{ color: '#6b7280' }}>{metadata.destination}</span>
                                            </>
                                        ) : 'All Regions'}
                                    </TableCell>
                                    <TableCell>{metadata.destination || 'N/A'}</TableCell>
                                    <TableCell>{metadata.timespan || 'N/A'}</TableCell>
                                    <TableCell>{generatedAt}</TableCell>
                                    <TableCell>
                                        <Button
                                            variant="contained"
                                            size="small"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onSelectAnalysis(analysis);
                                            }}
                                        >
                                            View
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>

            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                <Typography variant="body2" color="text.secondary">
                    Showing {filteredAnalyses.length} of {analyses.length} analyses
                    {filters.audience || filters.document_type || filters.origin ||
                        filters.destination || filters.timespan ?
                        <span style={{ backgroundColor: '#0072BC', color: 'white', 
                                     padding: '2px 6px', borderRadius: '4px', marginLeft: '8px', fontSize: '0.75rem' }}>
                            (filtered)
                        </span> : null}
                </Typography>
            </Box>
        </Box>
    );
}