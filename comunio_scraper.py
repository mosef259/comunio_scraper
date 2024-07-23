import requests
import argparse
import re
import csv
import os
from datetime import datetime
from bs4 import BeautifulSoup

url = "https://www.comunio.de/dashboard"
access_token = '64ad8047cbcb67d39d1e29782c92cf680f280efb'
headers = {
    'Authorization': access_token,
}

html_file_path = "html_content.txt"
transfers_file_path = "transfers.csv"
balance_file_path = "balances.csv"

latest_date = datetime.strptime("7/7/24", '%m/%d/%y')

player_names = ["Victor", "Passi", "Mike", "fifty", "Lennard", "Darius", "Christian", "Johannes", "Rouven", "Tennef", "Moritz"]
starting_balance = "20000000"

def parse_arguments():
    parser = argparse.ArgumentParser(description='Scrape transfer details from Comunio.')
    parser.add_argument('--mode', type=str, required=False, default="default", help='Mode to run in. \"reset\" to reset all transfers and balances')
    #parser.add_argument('--csv', type=str, required=False, help='The output CSV file name.')
    return parser.parse_args()

def extract_transfers(html_file_path):
    with open(html_file_path, 'r') as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    transfers = []


    print("Beginning extraction...")
    for daily_news_body in soup.find_all("div", class_='news_body_per_day animatable fold-animation'):
        for transfer_container in daily_news_body("div", attrs={"ng-if": "entry.type === 'TRANSACTION_TRANSFER'"}):
            for transfer in transfer_container('span', attrs={"translate": ""}):
                try:
                    player_tag = transfer.find('a', href=re.compile(r'/bundesliga/players/'))
                    player_name = player_tag.text if player_tag else None

                    text = transfer.get_text()
                    amount_match = re.search(r'transfers for ([\d,]+)', text)
                    amount = amount_match.group(1).replace(",", "") if amount_match else None

                    news_date = daily_news_body.find("div", class_="news_body_left news_date").text

                    from_computer_match = re.search(r'from (\w+)', text)
                    to_computer_match = re.search(r'to (\w+)', text)

                    if from_computer_match:
                        source_name = from_computer_match.group(1) if from_computer_match else None
                    else:
                        source_name = None

                    if to_computer_match:
                        target_name = to_computer_match.group(1) if to_computer_match else None
                    else:
                        target_name = None

                    if 'Computer' in [source_name, target_name]:
                        if source_name == 'Computer':
                            source_name = None
                        if target_name == 'Computer':
                            target_name = None

                    if (player_name != None):
                        transfers.append({
                                "Date": news_date,
                                'Source_Name': source_name,
                                "Target_Name": target_name,
                                'Amount': amount,
                                'Player_Name': player_name
                        })
                        
                except AttributeError:
                    continue


    transfers.sort(key=lambda x: parse_date(x['Date']))
    return transfers

def write_csv(transfers_file_path, balance_file_path, transfers):
    try:
        with open(transfers_file_path, mode='r') as csvfile:
            reader = csv.DictReader(csvfile)
            last_row = None
            for row in reader:
                last_row = row
            if last_row:
                latest_date = datetime.strptime(last_row['Date'], '%m/%d/%y ')
            else:
                latest_date = None
    except FileNotFoundError as e:
        print(e)
        return None

    new_transfers = [t for t in transfers if datetime.strptime(t['Date'], '%m/%d/%y ') > latest_date] if latest_date else transfers
    print(f"New transfers since {latest_date}:")
    if new_transfers:
        for t in new_transfers:
            print(t)
    else:
        print("None.")

    with open(transfers_file_path, mode='a', newline='') as csvfile:
        fieldnames = ['Date', 'Source_Name', 'Target_Name', 'Amount', 'Player_Name']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if latest_date is None:
            writer.writeheader()
        for transfer in new_transfers:
            writer.writerow(transfer)

    balances = []
    with open(balance_file_path, mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            balances.append(row)

    for b in balances:
        for nt in new_transfers:
            if (nt["Source_Name"] == b["Name"]):
                new_balance = int(b["Balance"]) + int(nt["Amount"].replace(",", ""))
                b["Balance"] = new_balance
            elif (nt["Target_Name"] == b["Name"]):
                new_balance = int(b["Balance"]) - int(nt["Amount"].replace(",", ""))
                b["Balance"] = new_balance

    print(f"New Balances:\n{balances}")
    with open(balance_file_path, mode="w", newline="") as csvfile:
        fieldnames = ["Name", "Balance"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for b in balances:
            writer.writerow(b)

def reset_balances(balance_file_path):
    balances = [{"Name": name, "Balance":starting_balance} for name in player_names]
    with open(balance_file_path, mode="w", newline="") as csvfile:
        fieldnames = ["Name", "Balance"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for b in balances:
            writer.writerow(b)

def reset_transfers(transfers_file_path):
    if os.path.exists(transfers_file_path):
        os.remove(transfers_file_path)

    with open(transfers_file_path, 'w') as file:
        pass


def parse_date(date_str):
    return datetime.strptime(date_str.strip(), '%m/%d/%y')

def get_html():
    #response = requests.get(url, headers=headers)

    #print(response)
    #print(f"encoding:{response.encoding}")
    #print(response.content)
    pass

def main():
    args = parse_arguments()
    mode = args.mode

    if mode == "default":
        transfers = extract_transfers(html_file_path)
        write_csv(transfers_file_path, balance_file_path, transfers)
    elif mode == "reset":
        print("Resetting everything.")
        reset_balances(balance_file_path)
        reset_transfers(transfers_file_path)

    
if __name__ == '__main__':
    main()
