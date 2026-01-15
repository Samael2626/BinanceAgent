# Changelog

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
