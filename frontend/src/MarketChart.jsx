import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, LineSeries, CrosshairMode, LineStyle } from 'lightweight-charts';

const MarketChart = ({ data, symbol, prediction }) => {
    const chartContainerRef = useRef();
    const rsiContainerRef = useRef();
    
    // Instance Refs
    const chartRef = useRef(null);
    const rsiChartRef = useRef(null);
    
    // Series Refs
    const candleSeriesRef = useRef(null);
    const sma50Ref = useRef(null);
    const sma200Ref = useRef(null);
    const projectionRef = useRef(null); // New Projection Series
    const rsiSeriesRef = useRef(null);
    
    // Zone Refs (Price Lines)
    const targetLineRef = useRef(null);
    const supportLineRef = useRef(null);

    // Tooltip State
    const [tooltipData, setTooltipData] = useState(null);
    const [tooltipVisible, setTooltipVisible] = useState(false);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

    const backgroundColor = '#0E1117';
    const gridColor = '#161A25';
    const textColor = '#848E9C';

    // Helper ref to access latest data inside event callbacks
    const latestDataRef = useRef(data);
    useEffect(() => { latestDataRef.current = data; }, [data]);

    // --- Chart Initialization ---
    useEffect(() => {
        if (!chartContainerRef.current || !rsiContainerRef.current) return;

        // 1. Create Main Chart
        const chart = createChart(chartContainerRef.current, {
            layout: { background: { type: ColorType.Solid, color: backgroundColor }, textColor },
            grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: { width: 1, color: '#555', style: LineStyle.Dashed },
                horzLine: { width: 1, color: '#555', style: LineStyle.Dashed },
            },
            timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2B3139' },
            rightPriceScale: { borderColor: '#2B3139' },
        });

        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#0ECB81', downColor: '#F6465D',
            borderVisible: false, wickUpColor: '#0ECB81', wickDownColor: '#F6465D',
        });
        const sma50Series = chart.addSeries(LineSeries, { color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: true, priceLineVisible: false });
        const sma200Series = chart.addSeries(LineSeries, { color: '#00B4C9', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: true, priceLineVisible: false });
        
        // Projection Series (Dotted)
        const projectionSeries = chart.addSeries(LineSeries, {
            color: '#0ECB81', 
            lineWidth: 2,
            lineStyle: LineStyle.Dotted,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false
        });

        chartRef.current = chart;
        candleSeriesRef.current = candleSeries;
        sma50Ref.current = sma50Series;
        sma200Ref.current = sma200Series;
        projectionRef.current = projectionSeries;

        // 2. Create RSI Chart
        const rsiChart = createChart(rsiContainerRef.current, {
            layout: { background: { type: ColorType.Solid, color: backgroundColor }, textColor },
            grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
            width: rsiContainerRef.current.clientWidth,
            height: 150,
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: { width: 1, color: '#555', style: LineStyle.Dashed },
                horzLine: { width: 1, color: '#555', style: LineStyle.Dashed, labelVisible: false },
            },
            timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#2B3139' },
            rightPriceScale: { borderColor: '#2B3139' },
            handleScale: { mouseWheel: false }
        });

        const rsiSeries = rsiChart.addSeries(LineSeries, { color: '#9370DB', lineWidth: 2 });
        rsiSeries.createPriceLine({ price: 70, color: 'rgba(246, 70, 93, 0.5)', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false });
        rsiSeries.createPriceLine({ price: 30, color: 'rgba(14, 203, 129, 0.5)', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false });
        
        rsiChartRef.current = rsiChart;
        rsiSeriesRef.current = rsiSeries;
        
        // ... (Sync logic omitted for brevity as it's unchanged) ...
        const mainTimeScale = chart.timeScale();
        const rsiTimeScale = rsiChart.timeScale();
        
        let isSyncingMain = false;
        let isSyncingRsi = false;

        mainTimeScale.subscribeVisibleLogicalRangeChange(range => {
            if (isSyncingRsi) return;
            if (range) {
                isSyncingMain = true;
                rsiTimeScale.setVisibleLogicalRange(range);
                isSyncingMain = false;
            }
        });

        rsiTimeScale.subscribeVisibleLogicalRangeChange(range => {
            if (isSyncingMain) return;
            if (range) {
                isSyncingRsi = true;
                mainTimeScale.setVisibleLogicalRange(range);
                isSyncingRsi = false;
            }
        });

        // 4. Tooltip Logic
        chart.subscribeCrosshairMove(param => {
            if (
                param.point === undefined || !param.time ||
                param.point.x < 0 || param.point.x > chartContainerRef.current.clientWidth ||
                param.point.y < 0 || param.point.y > chartContainerRef.current.clientHeight
            ) {
                setTooltipVisible(false);
                rsiChart.clearCrosshairPosition();
            } else {
                const rsiTime = param.time; 
                const priceData = param.seriesData.get(candleSeries);
                const sma50Data = param.seriesData.get(sma50Series);
                const sma200Data = param.seriesData.get(sma200Series);
                
                let rsiVal = null;
                if (latestDataRef.current) {
                    const item = latestDataRef.current.find(d => d.time === param.time);
                    if (item) rsiVal = item.rsi;
                }

                if (priceData) {
                    setTooltipData({
                        time: param.time,
                        open: priceData.open,
                        high: priceData.high,
                        low: priceData.low,
                        close: priceData.close,
                        sma50: sma50Data ? sma50Data.value : null,
                        sma200: sma200Data ? sma200Data.value : null,
                        rsi: rsiVal
                    });
                    setTooltipPos({ x: param.point.x, y: param.point.y });
                    setTooltipVisible(true);
                }
            }
        });

         const handleResize = () => {
             if (chartContainerRef.current) chart.applyOptions({ width: chartContainerRef.current.clientWidth });
             if (rsiContainerRef.current) rsiChart.applyOptions({ width: rsiContainerRef.current.clientWidth });
         };
         window.addEventListener('resize', handleResize);
 
         return () => {
             window.removeEventListener('resize', handleResize);
             chart.remove();
             rsiChart.remove();
         };
     }, []);
 
     // --- Data Updates ---
     useEffect(() => {
         if (!chartRef.current || !data || !Array.isArray(data)) return;
 
         const candles = [];
         const sma50 = [];
         const sma200 = [];
         const rsi = [];
 
         [...data].sort((a, b) => a.time - b.time).forEach(item => {
             if (item.time) {
                 candles.push({ time: item.time, open: item.open, high: item.high, low: item.low, close: item.close });
                 if (item.sma_50) sma50.push({ time: item.time, value: item.sma_50 });
                 if (item.sma_200) sma200.push({ time: item.time, value: item.sma_200 });
                 if (item.rsi) rsi.push({ time: item.time, value: item.rsi });
             }
         });
 
         if (candleSeriesRef.current) candleSeriesRef.current.setData(candles);
         if (sma50Ref.current) sma50Ref.current.setData(sma50);
         if (sma200Ref.current) sma200Ref.current.setData(sma200);
         if (rsiSeriesRef.current) rsiSeriesRef.current.setData(rsi);
 
         // --- Predictive Updates ---
         if (prediction && candleSeriesRef.current) {
             
             // 1. Projection Line
             if (prediction.projection && projectionRef.current) {
                 projectionRef.current.setData(prediction.projection);
             }
             
             // 2. Zones (Target & Support) - WITH ERROR HANDLING
             try {
                if (candleSeriesRef.current) {
                    // Start fresh logic to avoid removal error of non-existing lines?
                    // Checking if they exist in the Set of the series is hard.
                    // We just use try-catch on removal.
                    
                    try { if (targetLineRef.current) candleSeriesRef.current.removePriceLine(targetLineRef.current); } catch(e){}
                    try { if (supportLineRef.current) candleSeriesRef.current.removePriceLine(supportLineRef.current); } catch(e){}
                    
                    targetLineRef.current = null;
                    supportLineRef.current = null;
                    
                    if (prediction.zones && prediction.zones.target) {
                        targetLineRef.current = candleSeriesRef.current.createPriceLine({
                            price: prediction.zones.target,
                            color: 'rgba(14, 203, 129, 0.6)', 
                            lineWidth: 1,
                            lineStyle: LineStyle.Dotted,
                            axisLabelVisible: true,
                            title: 'TARGET',
                        });
                    }
                    
                    if (prediction.zones && prediction.zones.support) {
                        supportLineRef.current = candleSeriesRef.current.createPriceLine({
                            price: prediction.zones.support,
                            color: 'rgba(246, 70, 93, 0.6)', 
                            lineWidth: 1,
                            lineStyle: LineStyle.Dotted,
                            axisLabelVisible: true,
                            title: 'SUPPORT',
                        });
                    }
                }
             } catch (err) {
                 console.warn("Error drawing zones:", err);
             }
             
             // 3. Traps (Markers)
             try {
                 if (prediction.traps && prediction.traps.length > 0) {
                     const lastTime = candles[candles.length - 1]?.time;
                     if (lastTime) {
                         const markers = [];
                         prediction.traps.forEach(trap => {
                             if (trap === 'BULL_TRAP') {
                                 markers.push({ time: lastTime, position: 'aboveBar', color: '#F6465D', shape: 'arrowDown', text: 'Bull Trap' });
                             } else if (trap === 'BEAR_TRAP') {
                                 markers.push({ time: lastTime, position: 'belowBar', color: '#0ECB81', shape: 'arrowUp', text: 'Bear Trap' });
                             }
                         });
                         candleSeriesRef.current.setMarkers(markers);
                     }
                 } else {
                     candleSeriesRef.current.setMarkers([]);
                 }
             } catch(err) {
                 console.warn("Error drawing markers:", err);
             }
         }
 
     }, [data, prediction]);

    // Helpers for Header Display
    const currentData = latestDataRef.current && latestDataRef.current.length > 0 
        ? latestDataRef.current[latestDataRef.current.length - 1] 
        : null;

    const displayData = tooltipVisible && tooltipData ? tooltipData : {
        // Fallback to latest data
        open: currentData?.open,
        high: currentData?.high,
        low: currentData?.low,
        close: currentData?.close,
        sma50: currentData?.sma_50,
        sma200: currentData?.sma_200,
        rsi: currentData?.rsi
    };
     
    return (
        <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {/* Header Info */}
            <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 20, fontSize: '12px', fontFamily: 'Roboto, sans-serif', display: 'flex', gap: '15px', pointerEvents: 'none', color: '#848E9C' }}>
                 <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: '#EAECEF', fontWeight: 'bold', fontSize: '14px' }}>{symbol}</span>
                    {prediction && prediction.market_score !== undefined && (
                        <div style={{ 
                            background: prediction.market_score > 60 ? 'rgba(14, 203, 129, 0.2)' : prediction.market_score < 30 ? 'rgba(246, 70, 93, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                            border: `1px solid ${prediction.market_score > 60 ? '#0ECB81' : prediction.market_score < 30 ? '#F6465D' : '#848E9C'}`,
                            borderRadius: '4px',
                            padding: '2px 6px',
                            color: prediction.market_score > 60 ? '#0ECB81' : prediction.market_score < 30 ? '#F6465D' : '#EAECEF',
                            fontWeight: 'bold'
                        }}>
                            Score: {prediction.market_score}/100
                        </div>
                    )}
                </div>
                {/* Data Display */}
                {displayData.close && (
                    <>
                        <span>O: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81' }}>{displayData.open}</span></span>
                        <span>H: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81' }}>{displayData.high}</span></span>
                        <span>L: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81' }}>{displayData.low}</span></span>
                        <span>C: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81' }}>{displayData.close}</span></span>
                        {displayData.sma50 && <span style={{ color: '#FCD535' }}>MA(50): {displayData.sma50.toFixed(2)}</span>}
                        {displayData.sma200 && <span style={{ color: '#00B4C9' }}>MA(200): {displayData.sma200.toFixed(2)}</span>}
                        {displayData.rsi && <span style={{ color: '#9370DB' }}>RSI: {displayData.rsi.toFixed(2)}</span>}
                    </>
                )}
            </div>

            <div ref={chartContainerRef} style={{ width: '100%', height: '400px', borderRadius: '4px 4px 0 0', overflow: 'hidden' }} />
            <div ref={rsiContainerRef} style={{ width: '100%', height: '150px', borderRadius: '0 0 4px 4px', overflow: 'hidden' }} />
        </div>
    );
};

export default MarketChart;
