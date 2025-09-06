import requests
from bs4 import BeautifulSoup
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import sys
import select
from datetime import datetime
import threading
import signal
import queue
import os
from pathlib import Path


class Logger:
    def __init__(self, log_file="log.txt", discord_notifier=None):
        # For Mac, ensure we're using the script's directory or home directory
        if not os.path.isabs(log_file):
            # Try script directory first
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.log_file = os.path.join(script_dir, log_file)
        else:
            self.log_file = log_file
        
        # Store Discord notifier for log channel
        self.discord_notifier = discord_notifier
        
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create log directory: {e}")
        
        # Test write permissions on initialization
        self._test_write_permissions()
        
    def _test_write_permissions(self):
        """Test if we can write to the log file"""
        try:
            # Test write access
            with open(self.log_file, 'a', encoding='utf-8') as f:
                test_msg = f"# Log file test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f.write(test_msg)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            print(f"✅ Log file initialized successfully: {self.log_file}")
            print(f"✅ Log file absolute path: {os.path.abspath(self.log_file)}")
        except PermissionError:
            print(f"❌ Permission denied for log file: {self.log_file}")
            self._try_fallback_locations()
        except Exception as e:
            print(f"❌ Cannot write to log file {self.log_file}: {e}")
            self._try_fallback_locations()

    def _try_fallback_locations(self):
        """Try alternative log file locations"""
        fallback_locations = [
            os.path.join(os.path.expanduser("~"), "arbitrage_log.txt"),
            os.path.join(os.path.expanduser("~"), "Desktop", "arbitrage_log.txt"),
            os.path.join("/tmp", "arbitrage_log.txt"),
            os.path.join(os.getcwd(), "arbitrage_log_fallback.txt")
        ]
        
        for fallback_log in fallback_locations:
            try:
                with open(fallback_log, 'a', encoding='utf-8') as f:
                    test_msg = f"# Fallback log file test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f.write(test_msg)
                    f.flush()
                    os.fsync(f.fileno())
                self.log_file = fallback_log
                print(f"✅ Using fallback log file: {self.log_file}")
                return
            except Exception as e:
                print(f"❌ Fallback location {fallback_log} failed: {e}")
                continue
        
        print("❌ All log file locations failed. Logging to file will be disabled.")
        self.log_file = None
        
    def log_and_print(self, message):
        """Print to console, log to file, and send to Discord log channel"""
        # Always print to console first
        print(message)
        sys.stdout.flush()
        
        # Try to write to log file
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{message}\n")
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk on Mac
            except Exception as e:
                print(f"Warning: Could not write to log file: {e}")
                self.log_file = None  # Disable logging if it keeps failing
        
        # Send to Discord log channel
        if self.discord_notifier:
            # Format message for Discord (escape markdown characters and limit length)
            discord_message = self._format_for_discord(message)
            self.discord_notifier.send_log_message(discord_message)
    
    def _format_for_discord(self, message):
        """Format message for Discord, handling long messages and special characters"""
        # Escape markdown characters that might interfere
        message = message.replace('`', '\\`').replace('*', '\\*').replace('_', '\\_')
        
        # Discord has a 2000 character limit per message
        if len(message) > 1900:  # Leave some buffer
            return message[:1900] + "... (truncated)"
        
        return message


class DiscordNotifier:
    def __init__(self, webhook_url, log_webhook_url=None, username="Arbitrage Monitor"):
        self.webhook_url = webhook_url
        self.log_webhook_url = log_webhook_url
        self.username = username
        
    def send_message(self, message, to_log_channel=False):
        """Send a message to Discord via webhook"""
        try:
            webhook_to_use = self.log_webhook_url if to_log_channel and self.log_webhook_url else self.webhook_url
            
            data = {
                'content': message,
                'username': self.username
            }
            response = requests.post(webhook_to_use, json=data, timeout=10)
            if response.status_code == 204:
                return True
            else:
                print(f"Discord webhook failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"Discord notification error: {e}")
            return False
            
    def send_log_message(self, message):
        """Send a message specifically to the log channel"""
        if not self.log_webhook_url:
            return False
        return self.send_message(message, to_log_channel=True)
    
    def send_arbitrage_alert(self, url_label, margin, prices, odds):
        """Send a formatted arbitrage opportunity alert"""
        message = f"🎯 **ARBITRAGE OPPORTUNITY!**\n"
        message += f"📊 Market: {url_label}\n"
        message += f"💰 Margin: {margin:.2f}%\n"
        message += f"🏷️ Prices: {prices}\n"
        message += f"📈 Odds: {[round(odd, 2) for odd in odds]}\n"
        message += f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}"
        
        # Add @everyone mention for high margin opportunities (>5%)
        if margin > 5.0:
            message = f"@everyone\n\n{message}"
        
        return self.send_message(message)
    
    def send_summary(self, total_urls, opportunities):
        """Send a summary of all checked URLs"""
        if opportunities:
            message = f"📋 **SCAN SUMMARY** - {datetime.now().strftime('%H:%M:%S')}\n"
            message += f"🔍 Checked {total_urls} markets\n"
            message += f"🎯 Found {len(opportunities)} opportunities:\n"
            for url_label, margin in opportunities:
                message += f"  • {url_label}: {margin:.2f}%\n"
        else:
            message = f"📋 **SCAN SUMMARY** - {datetime.now().strftime('%H:%M:%S')}\n"
            message += f"🔍 Checked {total_urls} markets\n"
            message += f"❌ No arbitrage opportunities found"
        
        return self.send_message(message)


class ArbitrageMonitor:
    def __init__(self, urls, price_class, outcome_class, webhook_url, log_webhook_url=None, check_interval_minutes=5, logger=None):
        self.urls = urls if isinstance(urls, list) else [urls]  # Support both single URL and list
        self.price_class = price_class
        self.outcome_class = outcome_class
        self.check_interval_minutes = check_interval_minutes
        self.check_interval_seconds = check_interval_minutes * 60  # Convert to seconds
        self.running = True
        
        # Initialize Discord notifier with both webhooks
        self.discord = DiscordNotifier(webhook_url, log_webhook_url) if webhook_url else None
        
        # Initialize logger with Discord notifier for log channel
        self.logger = logger or Logger("log.txt", self.discord)
        
        # Store last arbitrage data for trading (now per URL)
        self.last_data = {}
        for url in self.urls:
            self.last_data[url] = {
                'outcome_names': [],
                'yes_prices': [],
                'odds': [],
                'margin': 0
            }
        
    def print_and_log(self, message):
        """Helper method to print and log messages"""
        self.logger.log_and_print(message)
    
    def send_discord_notification(self, message):
        """Send notification to Discord if webhook is configured"""
        if self.discord:
            return self.discord.send_message(message)
        return False
    
    def get_url_label(self, url):
        """Generate a short label for URL display"""
        try:
            # Extract a meaningful part of the URL
            if 'polymarket.com' in url:
                # Extract event name from polymarket URLs
                parts = url.split('/')
                if 'event' in parts:
                    event_index = parts.index('event')
                    if event_index + 1 < len(parts):
                        event_name = parts[event_index + 1].replace('-', ' ')
                        return event_name[:30] + "..." if len(event_name) > 30 else event_name
            
            # Fallback: use domain + path
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path = parsed.path.split('/')[-1] if parsed.path else ''
            return f"{domain}/{path}"[:40]
        except:
            return url[:40] + "..." if len(url) > 40 else url
        
    def extract_outcome_names(self, url):
        """Extract outcome names from p tags with the specified class"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            
            # Mac-specific Chrome options
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                driver.get(url)
                time.sleep(3)
                
                outcome_names = []
                class_selector = self.outcome_class.replace(' ', '.')
                elements = driver.find_elements(By.CSS_SELECTOR, f"p.{class_selector}")
                
                for element in elements:
                    try:
                        content = element.text.strip()
                        if content:
                            outcome_names.append(content)
                    except:
                        continue
                
                # Alternative method if CSS selector doesn't work
                if not outcome_names:
                    all_p_tags = driver.find_elements(By.TAG_NAME, "p")
                    for element in all_p_tags:
                        try:
                            element_class = element.get_attribute("class") or ""
                            if all(cls in element_class for cls in self.outcome_class.split()):
                                content = element.text.strip()
                                if content:
                                    outcome_names.append(content)
                        except:
                            continue
                
                return outcome_names
                    
            finally:
                driver.quit()
                
        except Exception as e:
            self.print_and_log(f"Selenium extraction failed for {self.get_url_label(url)}: {e}")
            return self.extract_outcome_names_beautifulsoup(url)

    def extract_outcome_names_beautifulsoup(self, url):
        """Fallback method using BeautifulSoup for outcome names"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            outcome_names = []
            
            target_p_tags = soup.find_all('p', class_=self.outcome_class)
            
            for p_tag in target_p_tags:
                content = p_tag.get_text(strip=True)
                if content:
                    outcome_names.append(content)
            
            return outcome_names
            
        except Exception as e:
            self.print_and_log(f"BeautifulSoup extraction failed for {self.get_url_label(url)}: {e}")
            return []

    def extract_yes_prices(self, url):
        """Extract yes prices from divs and return as float list"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            
            # Mac-specific Chrome options
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                driver.get(url)
                time.sleep(3)
                
                yes_prices = []
                class_selector = self.price_class.replace(' ', '.')
                elements = driver.find_elements(By.CSS_SELECTOR, f"div.{class_selector}")
                
                for element in elements:
                    try:
                        content = element.text.strip()
                        
                        if 'yes' in content.lower():
                            yes_price_matches = re.findall(r'yes[^¢]*?(\d+(?:\.\d+)?)¢', content.lower())
                            
                            for match in yes_price_matches:
                                yes_prices.append(float(match))
                            
                            if not yes_price_matches:
                                decimal_matches = re.findall(r'yes[^\d]*?(\d+(?:\.\d+)?)', content.lower())
                                for match in decimal_matches:
                                    try:
                                        price = float(match)
                                        if 0 < price <= 100:
                                            yes_prices.append(price)
                                    except:
                                        continue
                                        
                    except:
                        continue
                
                # Alternative method if CSS selector doesn't work
                if not yes_prices:
                    all_divs = driver.find_elements(By.TAG_NAME, "div")
                    for element in all_divs:
                        try:
                            element_class = element.get_attribute("class") or ""
                            if all(cls in element_class for cls in self.price_class.split()):
                                content = element.text.strip()
                                
                                if 'yes' in content.lower():
                                    yes_price_matches = re.findall(r'yes[^¢]*?(\d+(?:\.\d+)?)¢', content.lower())
                                    
                                    for match in yes_price_matches:
                                        yes_prices.append(float(match))
                                    
                                    if not yes_price_matches:
                                        decimal_matches = re.findall(r'yes[^\d]*?(\d+(?:\.\d+)?)', content.lower())
                                        for match in decimal_matches:
                                            try:
                                                price = float(match)
                                                if 0 < price <= 100:
                                                    yes_prices.append(price)
                                            except:
                                                continue
                        except:
                            continue
                
                return yes_prices
                    
            finally:
                driver.quit()
                
        except Exception as e:
            self.print_and_log(f"Selenium price extraction failed for {self.get_url_label(url)}: {e}")
            return self.extract_yes_prices_beautifulsoup(url)

    def extract_yes_prices_beautifulsoup(self, url):
        """Fallback method using BeautifulSoup"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            yes_prices = []
            
            target_divs = soup.find_all('div', class_=self.price_class)
            
            for div in target_divs:
                content = div.get_text(strip=True)
                
                if 'yes' in content.lower():
                    yes_price_matches = re.findall(r'yes[^¢]*?(\d+(?:\.\d+)?)¢', content.lower())
                    
                    for match in yes_price_matches:
                        yes_prices.append(float(match))
                    
                    if not yes_price_matches:
                        decimal_matches = re.findall(r'yes[^\d]*?(\d+(?:\.\d+)?)', content.lower())
                        for match in decimal_matches:
                            try:
                                price = float(match)
                                if 0 < price <= 100:
                                    yes_prices.append(price)
                            except:
                                continue
            
            return yes_prices
            
        except Exception as e:
            self.print_and_log(f"BeautifulSoup price extraction failed for {self.get_url_label(url)}: {e}")
            return []

    def calculate_arbitrage_margin(self, yes_prices):
        """Calculate arbitrage margin from yes prices"""
        if not yes_prices:
            return None, None
            
        odds = [100/price for price in yes_prices]
        arbitrage_constant = sum(1/odd for odd in odds)
        margin = (100/arbitrage_constant)-100
        
        return margin, odds

    def check_for_input_mac(self):
        """Mac-optimized input checking"""
        try:
            # Use select with a very short timeout
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                user_input = sys.stdin.readline().strip().lower()
                return user_input
        except Exception as e:
            pass
        return None

    def display_trading_table(self, url, yes_prices, odds, outcome_names, stake, arbitrage_constant):
        """Display the trading distribution table and send to Discord"""
        url_label = self.get_url_label(url)
        
        # Console/log output
        self.print_and_log(f"\n🎯 Trading table for: {url_label}")
        self.print_and_log("Distribution of the stake among the odds should be as follows:")
        
        # Build Discord message
        discord_message = f"🎯 **TRADING TABLE**\n"
        discord_message += f"📊 Market: {url_label}\n"
        discord_message += f"💰 Total Stake: {stake}\n\n"
        
        if outcome_names and len(outcome_names) >= len(yes_prices):
            self.print_and_log("\n{:<15} | {:<12} | {:<8} | {:<10} | {:<10}".format("Outcome Name", "Yes Price", "Odd", "Stake", "Payout"))
            self.print_and_log("-" * 70)
            
            discord_message += "```\n"
            discord_message += f"{'Outcome':<12} | {'Price':<8} | {'Stake':<8} | {'Payout':<8}\n"
            discord_message += "-" * 45 + "\n"
            
            for i in range(len(yes_prices)):
                stake_amount = stake * ((1/odds[i]) / arbitrage_constant)
                payout_amount = odds[i] * stake_amount
                outcome_name = outcome_names[i] if i < len(outcome_names) else f"Option {i+1}"
                
                self.print_and_log("{:<15} | {:<12} | {:<8.2f} | {:<10.2f} | {:<10.2f}".format(
                    outcome_name, yes_prices[i], odds[i], stake_amount, payout_amount))
                
                short_name = outcome_name[:10] + "..." if len(outcome_name) > 10 else outcome_name
                discord_message += f"{short_name:<12} | {yes_prices[i]:<8} | {stake_amount:<8.2f} | {payout_amount:<8.2f}\n"
        else:
            self.print_and_log("\n{:<12} | {:<8} | {:<10} | {:<10}".format("Yes Price", "Odd", "Stake", "Payout"))
            self.print_and_log("-" * 50)
            
            discord_message += "```\n"
            discord_message += f"{'Price':<8} | {'Stake':<8} | {'Payout':<8}\n"
            discord_message += "-" * 30 + "\n"
            
            for i in range(len(yes_prices)):
                stake_amount = stake * ((1/odds[i]) / arbitrage_constant)
                payout_amount = odds[i] * stake_amount
                
                self.print_and_log("{:<12} | {:<8.2f} | {:<10.2f} | {:<10.2f}".format(
                    yes_prices[i], odds[i], stake_amount, payout_amount))
                
                discord_message += f"{yes_prices[i]:<8} | {stake_amount:<8.2f} | {payout_amount:<8.2f}\n"

        total_profit = stake * ((1/arbitrage_constant)-1)
        self.print_and_log(f"\nTotal profit would be: {total_profit:.2f}")
        
        discord_message += "```\n"
        discord_message += f"💵 **Total Profit: {total_profit:.2f}**"
        
        # Send to Discord
        self.send_discord_notification(discord_message)

    def check_arbitrage_single_url(self, url):
        """Check for arbitrage opportunities for a single URL"""
        url_label = self.get_url_label(url)
        
        # Extract data
        outcome_names = self.extract_outcome_names(url)
        yes_prices = self.extract_yes_prices(url)
        
        if not yes_prices:
            self.print_and_log(f"❌ [{url_label}] No prices found.")
            return
        
        # Calculate arbitrage margin
        margin, odds = self.calculate_arbitrage_margin(yes_prices)
        
        if margin is None:
            self.print_and_log(f"❌ [{url_label}] Could not calculate arbitrage margin.")
            return
        
        # Display results
        self.print_and_log(f"🌐 Checked for: [{url_label}]")
        self.print_and_log(f"📊 Found {len(yes_prices)} outcomes")
        self.print_and_log(f"🏷️  Prices: {yes_prices}")
        self.print_and_log(f"📈 Odds: {[round(odd, 2) for odd in odds]}")
        self.print_and_log(f"💰 Arbitrage margin: {margin:.2f}%")
        
        
        if margin > 0:
            self.print_and_log(f"🎯 Arbitrage opportunity exists!")
            # Send Discord alert for profitable opportunities
            if self.discord:
                self.discord.send_arbitrage_alert(url_label, margin, yes_prices, odds)
        else:
            self.print_and_log(f"❌ No arbitrage opportunity (negative margin).")
        
        # Store data for potential trading
        self.last_data[url] = {
            'outcome_names': outcome_names,
            'yes_prices': yes_prices,
            'odds': odds,
            'margin': margin
        }

    def check_arbitrage(self):
        """Check for arbitrage opportunities across all URLs"""
        self.print_and_log(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking {len(self.urls)} URLs for arbitrage opportunities...")
        
        for i, url in enumerate(self.urls, 1):
            self.print_and_log(f"\n--- URL {i}/{len(self.urls)} ---")
            self.check_arbitrage_single_url(url)
        
        # Summary of arbitrage opportunities
        opportunities = []
        for url, data in self.last_data.items():
            if data['margin'] > 0:
                opportunities.append((self.get_url_label(url), data['margin']))
        
        if opportunities:
            self.print_and_log(f"\n🎯 SUMMARY: Found {len(opportunities)} arbitrage opportunities!")
            for url_label, margin in opportunities:
                self.print_and_log(f"   • {url_label}: {margin:.2f}%")
        else:
            self.print_and_log(f"\n❌ SUMMARY: No arbitrage opportunities found across {len(self.urls)} URLs.")
        
        # Send summary to Discord
        if self.discord:
            self.discord.send_summary(len(self.urls), opportunities)

    def show_all_trades(self):
        """Show all available trades (both profitable and non-profitable)"""
        all_trades = []
        for i, (url, data) in enumerate(self.last_data.items(), 1):
            if data['yes_prices']:  # Only show trades with valid price data
                all_trades.append((i, url, data))
        
        if not all_trades:
            self.print_and_log("❌ No trade data available. Please wait for at least one scraping cycle to complete.")
            return None
        
        self.print_and_log(f"\n📊 Available trades (showing all {len(all_trades)} markets):")
        
        # Build Discord message for all trades
        discord_message = f"📊 **ALL AVAILABLE TRADES**\n"
        discord_message += f"🔍 Total markets: {len(all_trades)}\n\n"
        
        for i, url, data in all_trades:
            status = "🎯 PROFITABLE" if data['margin'] > 0 else "❌ Not profitable"
            url_label = self.get_url_label(url)
            
            self.print_and_log(f"   {i}. {url_label} - {data['margin']:.2f}% margin ({status})")
            discord_message += f"{i}. {url_label}\n   Margin: {data['margin']:.2f}% {('🎯' if data['margin'] > 0 else '❌')}\n\n"
        
        # Send to Discord
        self.send_discord_notification(discord_message)
        
        return all_trades

    def handle_trade_command(self):
        """Handle the trade command interaction"""
        all_trades = self.show_all_trades()
        if not all_trades:
            return
        
        try:
            choice = input("\nEnter the number of the trade you want to calculate: ")
            choice_num = int(choice)
            if 1 <= choice_num <= len(all_trades):
                selected_trade = all_trades[choice_num - 1]
                _, selected_url, selected_data = selected_trade
                
                # Show trade details
                url_label = self.get_url_label(selected_url)
                self.print_and_log(f"\n📋 Trade details for: {url_label}")
                self.print_and_log(f"   Margin: {selected_data['margin']:.2f}%")
                self.print_and_log(f"   Prices: {selected_data['yes_prices']}")
                self.print_and_log(f"   Outcomes: {selected_data['outcome_names']}")
                
                if selected_data['margin'] <= 0:
                    self.print_and_log("⚠️  Warning: This trade has a negative margin - you would lose money!")
                    confirm = input("Do you still want to calculate stake distribution? (y/n): ")
                    if confirm.lower() not in ['y', 'yes']:
                        self.print_and_log("Trade calculation cancelled.")
                        return
                
                stake = float(input("Enter your stake: "))
                if stake > 0:
                    arbitrage_constant = sum(1/odd for odd in selected_data['odds'])
                    self.display_trading_table(
                        selected_url,
                        selected_data['yes_prices'], 
                        selected_data['odds'], 
                        selected_data['outcome_names'], 
                        stake, 
                        arbitrage_constant
                    )
                else:
                    self.print_and_log("Invalid stake amount.")
            else:
                self.print_and_log("Invalid choice.")
        except ValueError:
            self.print_and_log("Invalid input.")
        except (EOFError, KeyboardInterrupt):
            self.print_and_log("Trade calculation cancelled.")

    def run(self):
        """Main monitoring loop with proper timing"""
        self.print_and_log(f"🚀 Starting multi-URL arbitrage monitor...")
        self.print_and_log(f"⏰ Check interval: {self.check_interval_minutes} minutes")
        self.print_and_log(f"🌐 Monitoring {len(self.urls)} URLs:")
        for i, url in enumerate(self.urls, 1):
            self.print_and_log(f"   {i}. {self.get_url_label(url)}")
        self.print_and_log(f"📝 Log file: {self.logger.log_file}")
        self.print_and_log(f"🖥️  Platform: macOS")
        
        if self.discord:
            self.print_and_log(f"📢 Discord notifications: Enabled")
            self.print_and_log(f"📢 Discord log channel: {'Enabled' if self.discord.log_webhook_url else 'Disabled'}")
            # Send startup notification
            startup_msg = f"🚀 **ARBITRAGE MONITOR STARTED**\n"
            startup_msg += f"⏰ Check interval: {self.check_interval_minutes} minutes\n"
            startup_msg += f"🌐 Monitoring {len(self.urls)} markets\n"
            startup_msg += f"🖥️ Platform: macOS"
            self.discord.send_message(startup_msg)
        else:
            self.print_and_log(f"📢 Discord notifications: Disabled")
            
        self.print_and_log(f"ℹ️  Press Ctrl+C to stop monitoring")
        self.print_and_log(f"💡 Type 'trade' + Enter anytime to see all trades\n")
        
        try:
            while self.running:
                # Check arbitrage first
                self.check_arbitrage()
                
                # Now wait for the specified interval
                self.print_and_log(f"⏳ Waiting {self.check_interval_minutes} minutes until next check.")
                self.print_and_log(f"📝 Type 'trade' + Enter to see all available trades.")
                
                # Break the sleep into small chunks to check for input
                sleep_chunk = 0.5  # Check every 0.5 seconds on Mac
                elapsed_wait = 0
                
                while elapsed_wait < self.check_interval_seconds and self.running:
                    time.sleep(sleep_chunk)
                    elapsed_wait += sleep_chunk
                    
                    # Check for user input
                    user_input = self.check_for_input_mac()
                    if user_input:
                        if user_input in ['trade', 'yes', 'y']:
                            self.handle_trade_command()
                        elif user_input in ['quit', 'exit', 'stop']:
                            self.print_and_log("Stopping monitor...")
                            if self.discord:
                                self.discord.send_message("🛑 **ARBITRAGE MONITOR STOPPED**")
                            self.running = False
                            break
                        else:
                            self.print_and_log("Type 'trade' to see all trades or 'quit' to stop.")
                    
        except KeyboardInterrupt:
            self.print_and_log("\n\n🛑 Monitoring stopped by user.")
            if self.discord:
                self.discord.send_message("🛑 **ARBITRAGE MONITOR STOPPED** (Manual interruption)")
            self.running = False
        except Exception as e:
            self.print_and_log(f"\n❌ Error occurred: {e}")
            self.print_and_log("Monitoring stopped.")
            if self.discord:
                self.discord.send_message(f"❌ **ARBITRAGE MONITOR ERROR**\nError: {str(e)}")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Received interrupt signal. Stopping monitor...")
    try:
        # Try to find the log file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(script_dir, "log.txt")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n\n🛑 Received interrupt signal. Stopping monitor...\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Could not write to log file on exit: {e}")
    sys.exit(0)


# Main execution
if __name__ == "__main__":
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Print current working directory and script location for debugging
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")

    # Configurations
    # Configurations
    # Configurations
    # Configurations
    # Configurations
    
    #ADD YOUR URLS HERE
    urls = [
            "https://polymarket.com/event/elon-musk-of-tweets-august-29-september-5",
            "https://polymarket.com/event/bitcoin-price-on-september-5?tid=1756601598730",
            "https://polymarket.com/event/ethereum-price-on-september-5?tid=1756601602539",
            "https://polymarket.com/event/solana-price-on-september-5?tid=1756601600579"
    ]
    
    webhook_url = 'https://discord.com/api/webhooks/1411094569852080230/_hWFPQpX1XSLqeF52o0_ci6LC6MIp3LNBEgnd7TEgKrAbFLx4Ny4tQCad2H6GEwy6wh8'
    log_webhook_url = 'https://discord.com/api/webhooks/1411109425023811644/HzWKw4bXW9mklz5ZF9-yvxgzN9iDqjIJBuxZS2F3sGfiWPJOKHYyhISxL4GDmZtXW3_C'  #(set to None to disable)
    
    price_class = "c-dhzjXW c-dhzjXW-jVLVTy-zIndex-1 c-dhzjXW-bZmKkd-justifyContent-end c-dhzjXW-fVlWzK-gap-3"
    outcome_class = "c-dhzjXW c-dhzjXW-bZmKkd-justifyContent-end c-dhzjXW-jroWjL-alignItems-center"
    CHECK_INTERVAL_MINUTES = 0.5  # Change this to modify check frequency
    
    # Configurations
    # Configurations
    # Configurations
    # Configurations
    # Configurations

    # Initialize Discord notifier first (for logger)
    discord_notifier = DiscordNotifier(webhook_url, log_webhook_url) if webhook_url else None
    
    # Initialize logger with Discord notifier
    logger = Logger("log.txt", discord_notifier)
    
    # Log startup information
    logger.log_and_print(f"\n{'='*60}")
    logger.log_and_print(f"Multi-URL Arbitrage Monitor Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log_and_print(f"Running from: {os.getcwd()}")
    logger.log_and_print(f"Script location: {os.path.dirname(os.path.abspath(__file__))}")
    logger.log_and_print(f"Python executable: {sys.executable}")
    logger.log_and_print(f"Platform: macOS")
    logger.log_and_print(f"{'='*60}")
    
    # Create and run monitor
    monitor = ArbitrageMonitor(urls, price_class, outcome_class, webhook_url, log_webhook_url, CHECK_INTERVAL_MINUTES, logger)
    monitor.run()