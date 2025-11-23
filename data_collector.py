import csv
import time
import re
import ast
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

def grab_links():
    list_of_links = []
    url = "https://fightodds.io/recent-mma-events/ufc"
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    pattern = re.compile(r"^/mma-events/.*?/odds$", re.IGNORECASE)

    links = soup.find_all("a", href=lambda x: x and pattern.match(x))
    for link in links:
        href = link.get("href")
        url = "https://fightodds.io" + href[:-5] + "/fights"
        list_of_links.append(url)
    driver.quit()
    return list_of_links

def grab_odds_links(url):
    winnerKV = {}
    individual_odds_links = []
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(2)
    rows = driver.find_elements(By.XPATH, "//table/tbody//tr")
    for row in rows:
        if "def." in row.text:
            parts = row.text.split()
            key = " ".join(parts[1:parts.index("def.")])
            list_of_keywords = ["Decision", "KO", "TKO", "Submission"]
            for keyword in list_of_keywords:
                if keyword in parts:
                    winnerKV[key] = keyword
            link = row.find_element(By.XPATH, ".//a[contains(@class, 'MuiButton-root')]")
            href = link.get_attribute("href")
            individual_odds_links.append(href)
    driver.quit()
    return individual_odds_links, winnerKV

def odds_gatherer(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(5)

    buttons = driver.find_elements(By.TAG_NAME, "button")
    target_button = None

    for i, btn in enumerate(buttons):
        text = btn.text.strip()
        if "prop bets" in text.lower():
            target_button = btn

    if target_button:
        print("\nClicking Prop Bets button!.\n")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_button)
        time.sleep(0.4)
        target_button.click()
    else:
        print("didnt click button god damnit ")

    time.sleep(5)
    
    final_table = []
    rows_in_header = driver.find_elements(By.XPATH, "//table/thead//tr")
    for row in rows_in_header:
        cells = row.find_elements(By.XPATH, ".//th")
        values = [c.text.strip() for c in cells]
        if len(values) > 9:
            final_table.append(values)
        
    keywords = ["wins by decision", "wins by TKO/KO", "wins by submission"]
    rows_in_body = driver.find_elements(By.XPATH, "//table/tbody//tr")
    for row in rows_in_body:
        if any(keyword in row.text for keyword in keywords):
            row_values = []
            cells = row.find_elements(By.TAG_NAME, "td")
            for cell in cells:
                text = cell.text.strip()
                if text == "":
                    row_values.append(None)
                else:
                    row_values.append(cell.text)
            if len(row_values) > 1 and "%" not in row_values[1]:
                final_table.append(row_values)
    driver.quit()
    return final_table
odds_gatherer("https://fightodds.io/fights/arman-tsarukyan-vs-daniel-hooker-67200/odds")

def test(table):
    best_bets = {}
    for row in table:
        key = row[0]        
        value = row[1]        
        best_bets[key] = value
    return best_bets

def get_event_name(url):
    """
    Extracts the UFC event name from the URL.
    Example:
    https://fightodds.io/mma-events/6603/ufc-fight-night-265-tsarukyan-vs-hooker/fights
    -> "ufc-fight-night-265-tsarukyan-vs-hooker"
    """
    match = re.search(r"/([^/]+)/fights/?$", url)
    if match:
        return match.group(1)
    else:
        return "ufc-event"
      
def main():
    list_of_links = grab_links()
    # Just for testing, only grab the most recent x cards
    list_of_links = [list_of_links[5]]
    
    for link in list_of_links:
        # Get the card name
        card_name = get_event_name(link)
        print(f"\n{'='*60}")
        print(f"Card: {card_name}")
        print(f"{'='*60}\n")
        
        # Get all odds links for this card (winnerKV has actual results)
        all_odds_list, winnerKV = grab_odds_links(link)
        
        # Process each fight on the card
        for fight_num, event in enumerate(all_odds_list, 1):
            table = odds_gatherer(event)
            
            if table:
                # Get bet data for this fight
                bet_data = test(table)
                
                # Print fight header
                print(f"\nFight {fight_num}:")
                
                # Show actual result if available
                actual_winner = None
                for winner, method in winnerKV.items():
                    # Check if this winner appears in the bet data
                    for prop_name, odds_dict in bet_data.items():
                        if winner in odds_dict:
                            actual_winner = winner
                            print(f"  ✓ ACTUAL RESULT: {winner} by {method}")
                            break
                    if actual_winner:
                        break
                
                # Process and print predictions
                print_predictions(bet_data, actual_winner)
            else:
                print(f"\nFight {fight_num}:")
                print("  No odds data available")


def print_predictions(bet_data, actual_winner=None):
    """Process bet data and print predictions directly to console"""
    for prop_name, odds_dict in bet_data.items():
        if not odds_dict or len(odds_dict) < 2:
            continue
            
        # Convert to list of tuples and sort by odds value
        odds_list = [(fighter, odds) for fighter, odds in odds_dict.items() if odds]
        odds_list.sort(key=lambda x: int(x[1].replace('+', '').replace('-', '')))
        
        # Get predictions: lowest value + one more if within 50 points
        predictions = []
        if odds_list:
            first_fighter, first_odds = odds_list[0]
            first_num = int(first_odds.replace('+', '').replace('-', ''))
            
            # Mark if this was the actual winner
            marker = " ✓✓" if actual_winner and first_fighter == actual_winner else ""
            predictions.append(f"{first_fighter}: {first_odds}{marker}")
            
            # Check second value
            if len(odds_list) > 1:
                second_fighter, second_odds = odds_list[1]
                second_num = int(second_odds.replace('+', '').replace('-', ''))
                if abs(second_num - first_num) <= 50:
                    marker = " ✓✓" if actual_winner and second_fighter == actual_winner else ""
                    predictions.append(f"{second_fighter}: {second_odds}{marker}")
        
        if predictions:
            print(f"  {prop_name}: {' | '.join(predictions)}")


# Run it
main()