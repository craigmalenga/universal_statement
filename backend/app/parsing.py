# backend/app/parsing.py
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def parse_transactions(raw_content: str) -> pd.DataFrame:
    """
    Parse raw text content into structured transaction data
    """
    try:
        # Clean and preprocess the content
        content = preprocess_content(raw_content)
        
        # Try different parsing strategies
        transactions = []
        
        # Strategy 1: Standard UK bank format
        transactions = parse_standard_uk_format(content)
        
        # Strategy 2: Tabular format (if strategy 1 failed)
        if not transactions:
            transactions = parse_tabular_format(content)
        
        # Strategy 3: Line-by-line parsing (fallback)
        if not transactions:
            transactions = parse_line_by_line(content)
        
        if not transactions:
            logger.warning("No transactions found in content")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        
        # Clean and validate data
        df = clean_transaction_data(df)
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        logger.info(f"Successfully parsed {len(df)} transactions")
        return df
        
    except Exception as e:
        logger.error(f"Error parsing transactions: {str(e)}")
        return pd.DataFrame()

def preprocess_content(content: str) -> str:
    """
    Clean and preprocess content for parsing
    """
    if not content:
        return ""
    
    # Remove extra whitespace and normalize line breaks
    content = re.sub(r'\r\n|\r', '\n', content)
    content = re.sub(r'\n\s*\n', '\n', content)
    
    # Fix common formatting issues
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'(\d)\s+(\.\d{2})', r'\1\2', content)  # Fix decimal spacing
    content = re.sub(r'£\s+(\d)', r'£\1', content)  # Fix currency spacing
    
    return content.strip()

def parse_standard_uk_format(content: str) -> List[Dict[str, Any]]:
    """
    Parse standard UK bank statement format
    """
    transactions = []
    lines = content.split('\n')
    
    # Common UK date patterns
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{1,2}\s+\w{3}\s+\d{2,4})',      # DD MMM YYYY
        r'(\d{2}\w{3}\d{2,4})',              # DDMMMYYYY
    ]
    
    # Amount patterns
    amount_patterns = [
        r'£(\d+(?:,\d{3})*\.\d{2})',         # £1,234.56
        r'£(\d+\.\d{2})',                    # £123.45
        r'(\d+(?:,\d{3})*\.\d{2})',         # 1,234.56
        r'(\d+\.\d{2})',                     # 123.45
    ]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Try to find a date
        date_match = None
        for pattern in date_patterns:
            date_match = re.search(pattern, line)
            if date_match:
                break
        
        if not date_match:
            continue
        
        # Extract date
        date_str = date_match.group(1)
        parsed_date = parse_date(date_str)
        
        if not parsed_date:
            continue
        
        # Find amounts in the line
        amounts = []
        for pattern in amount_patterns:
            for match in re.finditer(pattern, line):
                amount_str = match.group(1) if match.groups() else match.group(0)
                amount_str = amount_str.replace('£', '').replace(',', '')
                try:
                    amount = float(amount_str)
                    amounts.append((amount, match.start(), match.end()))
                except ValueError:
                    continue
        
        if not amounts:
            continue
        
        # Extract description (text between date and amounts)
        date_end = date_match.end()
        first_amount_start = min(pos[1] for pos in amounts)
        
        description = line[date_end:first_amount_start].strip()
        description = re.sub(r'\s+', ' ', description)
        
        # Determine debit/credit and balance
        debit, credit, balance = categorize_amounts(amounts, line)
        
        transaction = {
            'date': parsed_date,
            'description': description,
            'debit': debit,
            'credit': credit,
            'balance': balance
        }
        
        transactions.append(transaction)
    
    return transactions

def parse_tabular_format(content: str) -> List[Dict[str, Any]]:
    """
    Parse tabular format with clear column separation
    """
    transactions = []
    lines = content.split('\n')
    
    # Look for header row
    header_idx = None
    columns = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(word in line_lower for word in ['date', 'description', 'amount', 'balance']):
            header_idx = i
            # Extract column positions
            columns = extract_column_positions(line)
            break
    
    if header_idx is None or not columns:
        return []
    
    # Parse data rows
    for line in lines[header_idx + 1:]:
        if not line.strip():
            continue
        
        # Extract values based on column positions
        values = extract_values_by_positions(line, columns)
        
        if len(values) < 3:  # Need at least date, description, amount
            continue
        
        # Parse transaction
        transaction = parse_tabular_row(values)
        if transaction:
            transactions.append(transaction)
    
    return transactions

def parse_line_by_line(content: str) -> List[Dict[str, Any]]:
    """
    Fallback parsing - try to extract transactions from each line
    """
    transactions = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if len(line) < 15:  # Too short to be a transaction
            continue
        
        # Look for date pattern
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
        if not date_match:
            continue
        
        date_str = date_match.group(1)
        parsed_date = parse_date(date_str)
        
        if not parsed_date:
            continue
        
        # Find amounts
        amounts = re.findall(r'£?(\d+(?:,\d{3})*\.\d{2})', line)
        if not amounts:
            continue
        
        # Convert amounts to float
        numeric_amounts = []
        for amount_str in amounts:
            try:
                amount = float(amount_str.replace(',', ''))
                numeric_amounts.append(amount)
            except ValueError:
                continue
        
        if not numeric_amounts:
            continue
        
        # Extract description (rough approximation)
        description_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+(.+?)\s+£?\d+', line)
        description = description_match.group(1).strip() if description_match else ""
        
        # Simple amount categorization
        if len(numeric_amounts) == 1:
            # Assume single amount is debit if negative context, else credit
            amount = numeric_amounts[0]
            if any(word in line.lower() for word in ['dr', 'debit', 'withdrawal', 'payment']):
                debit, credit, balance = amount, None, None
            else:
                debit, credit, balance = None, amount, None
        elif len(numeric_amounts) == 2:
            # Assume first is transaction, second is balance
            debit, credit, balance = numeric_amounts[0], None, numeric_amounts[1]
        else:
            # Take last as balance, try to categorize others
            balance = numeric_amounts[-1]
            transaction_amounts = numeric_amounts[:-1]
            debit = transaction_amounts[0] if transaction_amounts else None
            credit = None
        
        transaction = {
            'date': parsed_date,
            'description': description,
            'debit': debit,
            'credit': credit,
            'balance': balance
        }
        
        transactions.append(transaction)
    
    return transactions

def parse_date(date_str: str) -> Optional[str]:
    """
    Parse various date formats to YYYY-MM-DD
    """
    if not date_str:
        return None
    
    # Clean the date string
    date_str = re.sub(r'[^\d/\-\w\s]', '', date_str).strip()
    
    # Common date formats
    formats = [
        '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y',
        '%d %b %Y', '%d %B %Y', '%d%b%Y', '%d%b%y',
        '%Y-%m-%d', '%Y/%m/%d'
    ]
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Try more flexible parsing
    try:
        # Handle cases like "01Jan2024"
        match = re.match(r'(\d{1,2})(\w{3})(\d{2,4})', date_str)
        if match:
            day, month_abbr, year = match.groups()
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            
            month_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            month = month_map.get(month_abbr.lower())
            if month:
                return f"{year}-{month}-{day.zfill(2)}"
        
    except Exception:
        pass
    
    logger.warning(f"Could not parse date: {date_str}")
    return None

def categorize_amounts(amounts: List[Tuple[float, int, int]], line: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Categorize amounts as debit, credit, or balance
    """
    if not amounts:
        return None, None, None
    
    # Sort amounts by position in line
    amounts_sorted = sorted(amounts, key=lambda x: x[1])
    values = [amt[0] for amt in amounts_sorted]
    
    # Simple heuristics for categorization
    if len(values) == 1:
        # Single amount - check context for debit/credit
        amount = values[0]
        line_lower = line.lower()
        if any(word in line_lower for word in ['dr', 'debit', 'withdrawal', 'payment', 'fee']):
            return amount, None, None
        else:
            return None, amount, None
    
    elif len(values) == 2:
        # Two amounts - likely transaction amount and balance
        return values[0], None, values[1]
    
    elif len(values) == 3:
        # Three amounts - likely debit, credit, balance
        return values[0], values[1], values[2]
    
    else:
        # Multiple amounts - take last as balance, first as transaction
        return values[0], None, values[-1]

def extract_column_positions(header_line: str) -> List[Tuple[str, int, int]]:
    """
    Extract column names and their positions from header line
    """
    columns = []
    words = re.finditer(r'\S+', header_line)
    
    for match in words:
        word = match.group().lower()
        start, end = match.span()
        columns.append((word, start, end))
    
    return columns

def extract_values_by_positions(line: str, columns: List[Tuple[str, int, int]]) -> List[str]:
    """
    Extract values from line based on column positions
    """
    values = []
    
    for i, (col_name, start, end) in enumerate(columns):
        # Determine the end position for this column
        next_start = columns[i + 1][1] if i + 1 < len(columns) else len(line)
        
        # Extract value from the line
        value = line[start:next_start].strip()
        values.append(value)
    
    return values

def parse_tabular_row(values: List[str]) -> Optional[Dict[str, Any]]:
    """
    Parse a row of tabular data into a transaction
    """
    if len(values) < 3:
        return None
    
    # Assume first value is date
    date_str = values[0]
    parsed_date = parse_date(date_str)
    
    if not parsed_date:
        return None
    
    # Second value is description
    description = values[1]
    
    # Remaining values are amounts
    amounts = []
    for val in values[2:]:
        # Clean and parse amount
        clean_val = re.sub(r'[£$€,]', '', val).strip()
        if re.match(r'^-?\d+\.?\d*$', clean_val):
            try:
                amounts.append(float(clean_val))
            except ValueError:
                continue
    
    # Categorize amounts
    debit, credit, balance = None, None, None
    
    if len(amounts) >= 1:
        debit = amounts[0] if amounts[0] < 0 else None
        credit = amounts[0] if amounts[0] > 0 else None
    
    if len(amounts) >= 2:
        balance = amounts[-1]  # Last amount is typically balance
    
    return {
        'date': parsed_date,
        'description': description,
        'debit': abs(debit) if debit else None,
        'credit': credit,
        'balance': balance
    }

def clean_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate transaction data
    """
    if df.empty:
        return df
    
    # Ensure required columns exist
    required_columns = ['date', 'description', 'debit', 'credit', 'balance']
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    # Clean descriptions
    df['description'] = df['description'].fillna('').astype(str)
    df['description'] = df['description'].apply(lambda x: re.sub(r'\s+', ' ', x.strip()))
    
    # Ensure numeric columns are properly typed
    for col in ['debit', 'credit', 'balance']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Remove rows with no date
    df = df.dropna(subset=['date'])
    
    # Remove completely empty transactions
    df = df[
        df['description'].str.len() > 0 | 
        df['debit'].notna() | 
        df['credit'].notna() | 
        df['balance'].notna()
    ]
    
    return df