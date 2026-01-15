import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, LineSeries, CrosshairMode, LineStyle, HistogramSeries } from 'lightweight-charts';

const MarketChart = ({ data, symbol, prediction, entryPrice }) => {
    const chartContainerRef = useRef();
    const rsiContainerRef = useRef();
    
    // Instance Refs
    const chartRef = useRef(null);
    const rsiChartRef = useRef(null);
    
    // Series Refs
    const candleSeriesRef = useRef(null);
    const fastEmaRef = useRef(null);
    const trendEmaRef = useRef(null);
    const volumeSeriesRef = useRef(null); // New Volume Series
    const entryPriceLineRef = useRef(null); // New Entry Line
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
        const fastEmaSeries = chart.addSeries(LineSeries, { color: '#FCD535', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: true, priceLineVisible: false });
        const trendEmaSeries = chart.addSeries(LineSeries, { color: '#3B82F6', lineWidth: 2, crosshairMarkerVisible: false, lastValueVisible: true, priceLineVisible: false });
        
        // Volume Series (Overlay at the bottom)
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: '', // set as an overlay
        });
        chart.priceScale('').applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
        });
        
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
        fastEmaRef.current = fastEmaSeries;
        trendEmaRef.current = trendEmaSeries;
        volumeSeriesRef.current = volumeSeries;
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
                const fastEmaData = param.seriesData.get(fastEmaSeries);
                const trendEmaData = param.seriesData.get(trendEmaSeries);
                
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
                        fastEma: fastEmaData ? fastEmaData.value : null,
                        trendEma: trendEmaData ? trendEmaData.value : null,
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

         const observer = new ResizeObserver(handleResize);
         if (chartContainerRef.current) observer.observe(chartContainerRef.current);
 
         return () => {
             observer.disconnect();
             chart.remove();
             rsiChart.remove();
         };
     }, []);
 
     // --- Data Updates ---
     useEffect(() => {
         if (!chartRef.current || !data || !Array.isArray(data)) return;
 
         const candles = [];
         const fastEma = [];
         const trendEma = [];
         const volume = [];
         const rsi = [];
 
         [...data].sort((a, b) => a.time - b.time).forEach((item, index, arr) => {
             if (item.time) {
                 candles.push({ time: item.time, open: item.open, high: item.high, low: item.low, close: item.close });
                 if (item.fast_ema) fastEma.push({ time: item.time, value: item.fast_ema });
                 if (item.trend_ema) trendEma.push({ time: item.time, value: item.trend_ema });
                 if (item.rsi) rsi.push({ time: item.time, value: item.rsi });
                 
                 // Volume with color logic (Green if close > open)
                 if (item.volume !== undefined) {
                     volume.push({ 
                         time: item.time, 
                         value: item.volume, 
                         color: item.close >= item.open ? 'rgba(14, 203, 129, 0.4)' : 'rgba(246, 70, 93, 0.4)' 
                     });
                 }
             }
         });
 
         if (candleSeriesRef.current) candleSeriesRef.current.setData(candles);
         if (fastEmaRef.current) fastEmaRef.current.setData(fastEma);
         if (trendEmaRef.current) trendEmaRef.current.setData(trendEma);
         if (volumeSeriesRef.current) volumeSeriesRef.current.setData(volume);
          if (rsiSeriesRef.current) rsiSeriesRef.current.setData(rsi);
 
          // --- Entry Price Line logic ---
          if (candleSeriesRef.current) {
              try {
                  if (entryPriceLineRef.current) {
                      candleSeriesRef.current.removePriceLine(entryPriceLineRef.current);
                      entryPriceLineRef.current = null;
                  }
                  if (entryPrice > 0) {
                      entryPriceLineRef.current = candleSeriesRef.current.createPriceLine({
                          price: entryPrice,
                          color: '#FCD535',
                          lineWidth: 2,
                          lineStyle: LineStyle.Dashed,
                          axisLabelVisible: true,
                          title: 'COMPRA',
                      });
                  }
              } catch (e) { console.warn("Error entry line:", e); }
          }
 
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
                 if (candleSeriesRef.current && typeof candleSeriesRef.current.setMarkers === 'function') {
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
        fastEma: currentData?.fast_ema,
        trendEma: currentData?.trend_ema,
        rsi: currentData?.rsi
    };
     
    return (
        <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {/* Header Info */}
            {/* Header Info - Two Row Layout to prevent overlap */}
            <div style={{ 
                position: 'absolute', top: 10, left: 10, zIndex: 20, 
                fontSize: '11px', fontFamily: 'Inter, sans-serif', 
                display: 'flex', flexDirection: 'column', gap: '8px', 
                pointerEvents: 'none', color: '#848E9C' 
            }}>
                 {/* Row 1: Symbol & Score */}
                 <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: '#EAECEF', fontWeight: '950', fontSize: '13px', letterSpacing: '0.05em' }}>{symbol}</span>
                    {prediction && prediction.market_score !== undefined && (
                        <div style={{ 
                            background: prediction.market_score > 60 ? 'rgba(14, 203, 129, 0.2)' : prediction.market_score < 30 ? 'rgba(246, 70, 93, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                            border: `1px solid ${prediction.market_score > 60 ? '#0ECB81' : prediction.market_score < 30 ? '#F6465D' : '#848E9C'}`,
                            borderRadius: '4px',
                            padding: '2px 8px',
                            color: prediction.market_score > 60 ? '#0ECB81' : prediction.market_score < 30 ? '#F6465D' : '#EAECEF',
                            fontWeight: '900',
                            fontSize: '10px'
                        }}>
                            SCORE: {prediction.market_score}/100
                        </div>
                    )}
                </div>

                {/* Row 2: Price Data & Indicators */}
                {displayData.close && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '4px 8px', borderRadius: '4px', backdropFilter: 'blur(4px)' }}>
                        <div style={{ display: 'flex', gap: '8px', borderRight: '1px solid rgba(255,255,255,0.1)', paddingRight: '8px' }}>
                            <span>O: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81', fontWeight: '600' }}>{displayData.open}</span></span>
                            <span>H: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81', fontWeight: '600' }}>{displayData.high}</span></span>
                            <span>L: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81', fontWeight: '600' }}>{displayData.low}</span></span>
                            <span>C: <span style={{ color: displayData.open > displayData.close ? '#F6465D' : '#0ECB81', fontWeight: '600' }}>{displayData.close}</span></span>
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                            {displayData.fastEma && <span style={{ color: '#FCD535' }}>EMA Fast: <b style={{color: '#fff'}}>{displayData.fastEma.toFixed(2)}</b></span>}
                            {displayData.trendEma && <span style={{ color: '#3B82F6' }}>Trend EMA: <b style={{color: '#fff'}}>{displayData.trendEma.toFixed(2)}</b></span>}
                            {displayData.rsi && <span style={{ color: '#9370DB' }}>RSI: <b style={{color: '#fff'}}>{displayData.rsi.toFixed(2)}</b></span>}
                        </div>
                    </div>
                )}
            </div>

            <div ref={chartContainerRef} style={{ width: '100%', height: '400px', borderRadius: '4px 4px 0 0', overflow: 'hidden' }} />
            <div ref={rsiContainerRef} style={{ width: '100%', height: '150px', borderRadius: '0 0 4px 4px', overflow: 'hidden' }} />
        </div>
    );
};

export default MarketChart;
