# Multi-URL Arbitrage Monitor

A Python-based arbitrage monitoring tool that scrapes prediction markets (specifically designed for Polymarket) to identify profitable arbitrage opportunities across multiple betting outcomes. The tool automatically checks for price discrepancies that could result in guaranteed profits and provides Discord notifications for real-time alerts.

⚠️ Market Compatibility: This tool only works with complete, non-overlapping markets where all possible outcomes are covered and mutually exclusive.
✅ Compatible Markets:

Binary markets (Yes/No)
Complete categorical markets (e.g., "Which team will win?" covering all teams)
Exhaustive outcome markets (e.g., "Price range on date X" with ranges covering all possibilities)

❌ Incompatible Markets:

Overlapping outcome markets (e.g., "Will Bitcoin hit $50k?" and "Will Bitcoin hit $60k?" - both can be true)
Incomplete markets (missing possible outcomes)
Markets with "Other" or undefined categories
Conditional markets where outcomes aren't mutually exclusive

Example: A market asking "Will it rain tomorrow?" (Yes/No) works perfectly. A market with outcomes "Heavy rain" and "Light rain" doesn't work because "No rain" isn't covered, making arbitrage impossible.

The key point is that for arbitrage to work mathematically, you need to be able to bet on ALL possible outcomes of an event, and those outcomes must be mutually exclusive (only one can happen).

## Features

- **Multi-URL Monitoring**: Monitor multiple prediction markets simultaneously
- **Real-time Arbitrage Detection**: Automatically calculates arbitrage margins and identifies profitable opportunities
- **Discord Integration**: 
  - Instant notifications for arbitrage opportunities
  - Separate log channel for detailed monitoring
  - Summary reports after each scan cycle
- **Trading Calculator**: Interactive tool to calculate optimal stake distribution for identified opportunities
- **Robust Data Extraction**: Uses both Selenium and BeautifulSoup for reliable web scraping
- **Cross-platform Logging**: Comprehensive logging with fallback locations for different operating systems
- **Graceful Error Handling**: Continues monitoring even if individual URLs fail

## Requirements

### Python Dependencies
```bash
pip install requests beautifulsoup4 selenium
```

### Chrome WebDriver
This script requires Chrome WebDriver for Selenium automation. Install it using one of these methods:

#### Option 1: Using ChromeDriver Manager (Recommended)
```bash
pip install webdriver-manager
```

#### Option 2: Manual Installation
1. Download ChromeDriver from https://chromedriver.chromium.org/
2. Add it to your system PATH

## Configuration

### Required Setup
Before running the script, you need to configure several parameters in the `main.py` file:

#### 1. URLs to Monitor
Add the Polymarket URLs you want to monitor:
```python
urls = [
    "https://polymarket.com/event/your-first-market",
    "https://polymarket.com/event/your-second-market",
    # Add more URLs here
]
```

#### 2. Discord Webhooks (Optional but Recommended)
Create Discord webhooks for notifications:
```python
webhook_url = 'https://discord.com/api/webhooks/YOUR_MAIN_WEBHOOK'
log_webhook_url = 'https://discord.com/api/webhooks/YOUR_LOG_WEBHOOK'  # Optional
```

**To create Discord webhooks:**
1. Go to your Discord server settings
2. Navigate to Integrations → Webhooks
3. Create a new webhook and copy the URL
4. Optionally create a second webhook for detailed logs

#### 3. CSS Selectors
The script uses CSS selectors to extract data. Update these if Polymarket changes their structure:
```python
price_class = "c-dhzjXW c-dhzjXW-jVLVTy-zIndex-1 c-dhzjXW-bZmKkd-justifyContent-end c-dhzjXW-fVlWzK-gap-3"
outcome_class = "c-dhzjXW c-dhzjXW-bZmKkd-justifyContent-end c-dhzjXW-jroWjL-alignItems-center"
```

#### 4. Check Interval
Set how frequently to check for arbitrage opportunities:
```python
CHECK_INTERVAL_MINUTES = 5  # Check every 5 minutes
```

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/arbitrage-monitor.git
cd arbitrage-monitor
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure the script:**
   - Edit `main.py` to add your URLs and Discord webhooks
   - Adjust CSS selectors if necessary

4. **Run the script:**
```bash
python main.py
```

## Usage

### Starting the Monitor
```bash
python main.py
```

The script will:
- Start monitoring all configured URLs
- Check for arbitrage opportunities at the specified interval
- Send Discord notifications when opportunities are found
- Log all activities to a log file

### Interactive Commands
While the monitor is running, you can use these commands:

- **`trade`**: View all available trades and calculate stake distributions
- **`quit`** or **`exit`**: Stop the monitor
- **`Ctrl+C`**: Gracefully shutdown the monitor

### Understanding the Output

#### Console Output
```
🎯 ARBITRAGE OPPORTUNITY!
📊 Market: bitcoin-price-september-5
💰 Margin: 3.45%
🏷️ Prices: [45.2, 56.8]
📈 Odds: [2.21, 1.76]
⏰ Time: 14:30:15
```

#### Trading Table
When you select a trade, you'll see a detailed breakdown:
```
Trading table for: bitcoin-price-september-5
Distribution of the stake among the odds should be as follows:

Outcome Name    | Yes Price    | Odd      | Stake      | Payout    
----------------------------------------------------------------
Yes             | 45.2         | 2.21     | 452.49     | 1000.00   
No              | 56.8         | 1.76     | 547.51     | 1000.00   

Total profit would be: 34.50
```

## How Arbitrage Detection Works

The script identifies arbitrage opportunities by:

1. **Extracting Prices**: Scrapes "Yes" prices from each outcome in a market
2. **Converting to Odds**: Converts prices to decimal odds using: `Odd = 100 / Price`
3. **Calculating Arbitrage Constant**: Sums the inverse of all odds: `Σ(1/Odd)`
4. **Determining Margin**: Calculates profit margin: `(100/Arbitrage_Constant) - 100`

**Positive margin = Arbitrage opportunity exists**

## Logging

The script creates comprehensive logs including:
- All arbitrage checks and results
- Error messages and warnings
- Trading calculations
- System status updates

**Log file locations** (tries in order):
1. Same directory as script: `./log.txt`
2. Home directory: `~/arbitrage_log.txt`
3. Desktop: `~/Desktop/arbitrage_log.txt`
4. Temp directory: `/tmp/arbitrage_log.txt`

## Discord Notifications

### Main Channel Notifications
- 🎯 Arbitrage opportunities with details
- 📋 Scan summaries with opportunity counts
- 🚀 System startup/shutdown messages
- ⚠️ Critical errors

### Log Channel (Optional)
- Detailed monitoring logs
- All console output mirrored to Discord
- Technical debugging information

## Troubleshooting

### Common Issues

#### "No prices found"
- **Cause**: CSS selectors may be outdated due to website changes
- **Solution**: Inspect the webpage and update `price_class` and `outcome_class`

#### Chrome WebDriver errors
- **Cause**: ChromeDriver not installed or incompatible version
- **Solution**: Update ChromeDriver to match your Chrome version

#### Permission denied for log file
- **Cause**: Insufficient write permissions
- **Solution**: The script automatically tries fallback locations

#### Discord notifications not working
- **Cause**: Invalid webhook URL
- **Solution**: Verify webhook URLs are correct and active

### CSS Selector Updates

If Polymarket changes their website structure, you'll need to update the CSS selectors:

1. **Open browser developer tools** (F12)
2. **Inspect the price elements** and outcome name elements
3. **Copy the class names**
4. **Update the configuration** in `main.py`

## Legal and Ethical Considerations

- **Use Responsibly**: This tool is for educational purposes
- **Respect Terms of Service**: Ensure compliance with platform terms
- **Rate Limiting**: The script includes delays to avoid overwhelming servers
- **Risk Management**: Always verify opportunities manually before placing bets

## Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Create a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add comments for complex logic
- Test with multiple market types
- Update documentation as needed

## Version History

- **v1.0.0** - Initial release with multi-URL monitoring and Discord integration
- **Future versions** - See GitHub releases for updates

## Support and Contact

- **Issues**: Open an issue on GitHub
- **Feature Requests**: Create an issue with the "enhancement" label  

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

**⚠️ COMPREHENSIVE LEGAL DISCLAIMER**

### Educational Purpose Only
This software is provided **strictly for educational and research purposes**. It is designed to:
- Teach arbitrage concepts and market analysis techniques  
- Demonstrate web scraping and data analysis methods
- Provide a learning platform for understanding prediction markets
- **NOT to provide financial advice or guarantee profits**

### User Responsibilities
By using this software, you acknowledge and agree that:

#### Platform Compliance
- **Terms of Service**: You are solely responsible for compliance with Polymarket's Terms of Service and any other applicable platform policies
- **Automated Access**: Some platforms prohibit automated access - you must verify current terms before use
- **Account Risk**: Use of automated tools may violate platform terms and could result in account suspension or termination

#### Legal and Regulatory Compliance  
- **Jurisdiction Laws**: You must ensure that prediction market participation is legal in your jurisdiction
- **Regulatory Requirements**: You are responsible for compliance with all local gambling, financial, and tax regulations
- **Geographic Restrictions**: Access to prediction markets may be restricted in certain locations

#### Financial and Risk Considerations
- **No Financial Advice**: This software does not provide financial, investment, or trading advice
- **Independent Verification**: You must independently verify all calculations, opportunities, and market data
- **Financial Risk**: All trading involves risk of financial loss - never risk money you cannot afford to lose
- **No Guarantees**: No guarantee of profitability, accuracy, or successful arbitrage opportunities

#### Technical and Ethical Use
- **Responsible Scraping**: Do not modify rate limiting or delays - respect server resources
- **Educational Intent**: Use only for learning and research purposes, not for commercial exploitation  
- **Data Accuracy**: Market data may be delayed, inaccurate, or incomplete

### Limitation of Liability
The developers and contributors of this software:
- **Provide no warranties** of any kind, express or implied
- **Are not responsible** for any financial losses, legal issues, account suspensions, or other consequences
- **Make no representations** about the accuracy, completeness, or reliability of the software
- **Shall not be liable** for any direct, indirect, incidental, special, or consequential damages

### Changes to Terms and Markets
- **Platform Changes**: Prediction market platforms may change their terms, structure, or policies at any time
- **Legal Changes**: Laws and regulations regarding prediction markets may change
- **Software Updates**: This software may require updates to remain functional

### Final Warning
**Use this software at your own risk and discretion. The developers strongly recommend:**
- Consulting with legal and financial professionals before engaging in prediction market activities
- Starting with small amounts to understand the risks involved  
- Thoroughly reading and understanding all platform terms of service
- Ensuring compliance with all applicable laws and regulations in your jurisdiction

**By using this software, you acknowledge that you have read, understood, and agree to be bound by this disclaimer.**
