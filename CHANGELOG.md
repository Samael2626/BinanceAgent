# Changelog

## [2.0.0] - 2026-01-15

### 🔥 Major Architectural Shift
- **TradingEngine Core**: Complete refactoring of the bot's brain into a modular, service-oriented architecture.
- **OrderManager**: Centralized order handling with strict "Zero Residue" enforcement and real-time Binance filter validation.
- **MarketDataService**: Optimized data handling for consistent historical and real-time analysis.

### 🧠 Trading Intelligence
- **RSI Glide (Smart Trailing)**: New dynamic exit mechanism that follows upward trends and protects gains with institutional-grade precision.
- **Advanced Filtering**: Added ADX Trend Strength and Lateralization filters to filter out noise and improve entry quality.
- **Smart Matrix Integration**: Unified indicator processing for faster and more reliable decision making.

### ✨ Premium UX/UI
- **Majestic Dashboard**: Total redesign with glassmorphism effects, optimized grid spacing, and refined typography.
- **Elegance Monitor**: High-end RSI monitor panel with 4-column grid and premium visual effects.
- **Performance Optimization**: Smoother chart rendering and responsive layout adjustments.

### 🛠 Stability & Reliability
- **WebSocket Master**: Fixed shutdown race conditions and implemented high-resiliency connection management.
- **State Integrity**: Guaranteed synchronization between internal bot state and real Binance balances.
- **Multi-User Ready**: Hardened auth logic and session management.


## [1.9.0] - 2026-01-14

### Major Features
- **Predictive Engine Integration**: Full integration of `PredictiveEngine` for market analysis (RSI Divergences, RVOL, Bull/Bear Traps, Liquidity Zones).
- **Dynamic Risk Management (ATR)**: Added ATR-based Dynamic Take Profit to `rsi_rebound.py` strategy.
- **Smart Money Flow**: Added institutional volume analysis to detection logic.

### Improved
- **Bot Logic**: Updated to version 1.9.0 logic with enhanced state management.
- **Frontend**: Updated build version to match backend capabilities.

## [1.8.2] - 2026-01-14

### Added
- **Predictive Module**: New `predictive_modules.py` for price and trend prediction.
- **Predictive Dashboard**: Frontend component to visualize AI-driven market predictions.
- **Documentation**: Added documentation for the predictive module logic.

### Changed
- Refactored `PredictiveDashboard.jsx` for better error handling and UI performance.
- Improved RSI snapshot stability.
- Updated authentication logic to resolve session expiration issues.

## [1.8.1] - 2026-01-13

### Changed
- Updated version to 1.8.1.
- Cleaned up untracked debug files.
- Improved version tracking in backend and frontend.

### Removed
- Removed `diagnose_trade.py`.
- Removed `debug_bot_state_custom.py`.
- Removed `chart.png`.
