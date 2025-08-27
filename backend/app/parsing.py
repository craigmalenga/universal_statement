# backend/app/parsing.py - UNIVERSAL UK BANK PARSER
import pandas as pd
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def parse_transactions(raw_content: str) -> pd.DataFrame:
    """
    Universal bank statement parser for UK banks
    """
    try:
        # Clean content first
        content = preprocess_content(raw_content)
        
        # Extract all potential transaction lines
        all_transactions = []
        
        # Strategy 1: Extract ALL lines with dates and amounts
        logger.info("Attempting comprehensive extraction...")
        all_transactions = extract_all_transaction_lines(content)
        
        if len(all_transactions) < 5:  # Too few, try alternative methods
            logger.info(f"Only found {len(all_transactions)} transactions, trying alternative methods...")
            
            # Strategy 2: Table extraction with headers
            table_transactions = extract_table_transactions(content)
            if len(table_transactions) > len(all_transactions):
                all_transactions = table_transactions
            
            # Strategy 3: Block-based extraction (for PDFs that group text oddly)
            if len(all_transactions) < 5:
                block_transactions = extract_block_transactions(content)
                if len(block_transactions) > len(all_transactions):
                    all_transactions = block_transactions
        
        if not all_transactions:
            logger.warning("No transactions found")
            return pd.DataFrame()
        
        # Convert to DataFrame and clean
        df = pd.DataFrame(all_transactions)
        df = clean_and_validate_transactions(df)
        
        logger.info(f"Successfully parsed {len(df)} transactions")
        return df
        
    except Exception as e:
        logger.error(f"Error parsing transactions: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def preprocess_content(content: str) -> str:
    """
    Clean and normalize content for parsing
    """
    if not content:
        return ""
    
    # Fix common OCR issues
    replacements = {
        r'[Il|](\d)': r'1\1',  # I/l/| followed by digit -> 1
        r'(\d)[Il|]': r'\11',  # digit followed by I/l/| -> 1
        r'[Oo](\d)': r'0\1',  # O followed by digit -> 0
        r'(\d)[Oo]': r'\10',  # digit followed by O -> 0
        r'£\s+': '£',  # Remove spaces after £
        r'(\d)\s+\.\s*(\d)': r'\1.\2',  # Fix decimal spacing
        r'(\d),\s*(\d{3})': r'\1,\2',  # Fix thousand separator
    }
    
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
    
    return content

def extract_all_transaction_lines(content: str) -> List[Dict[str, Any]]:
    """
    Extract ALL lines that look like transactions (date + amounts)
    """
    transactions = []
    lines = content.split('\n')
    
    # Track which lines we've already processed
    processed_indices = set()
    
    for i, line in enumerate(lines):
        if i in processed_indices:
            continue
            
        line = line.strip()
        if not line or len(line) < 10:
            continue
        
        # Look for UK date formats
        date_patterns = [
            (r'(\d{2}/\d{2}/\d{4})', '%d/%m/%Y'),  # 31/07/2025
            (r'(\d{2}-\d{2}-\d{4})', '%d-%m-%Y'),  # 31-07-2025
            (r'(\d{2}/\d{2}/\d{2})', '%d/%m/%y'),  # 31/07/25
            (r'(\d{2}\s+\w{3}\s+\d{4})', '%d %b %Y'),  # 31 Jul 2025
            (r'(\d{2}\w{3}\d{2})', '%d%b%y'),  # 31Jul25
        ]
        
        transaction = None
        for date_pattern, date_format in date_patterns:
            date_match = re.search(date_pattern, line)
            if date_match:
                date_str = date_match.group(1)
                parsed_date = parse_date_flexible(date_str, date_format)
                
                if parsed_date:
                    # Found a date, now extract the transaction
                    transaction = extract_transaction_from_line(
                        line, date_str, parsed_date, date_match.span()
                    )
                    if transaction:
                        transactions.append(transaction)
                        processed_indices.add(i)
                        break
        
        # If no transaction found on this line, check if it might be multi-line
        if not transaction and i < len(lines) - 1:
            # Check if next line has amounts but no date (continuation)
            next_line = lines[i + 1].strip()
            if re.search(r'-?\d+\.\d{2}', next_line) and not re.search(r'\d{2}[/-]\d{2}', next_line):
                # Combine lines and retry
                combined = line + ' ' + next_line
                for date_pattern, date_format in date_patterns:
                    date_match = re.search(date_pattern, combined)
                    if date_match:
                        date_str = date_match.group(1)
                        parsed_date = parse_date_flexible(date_str, date_format)
                        if parsed_date:
                            transaction = extract_transaction_from_line(
                                combined, date_str, parsed_date, date_match.span()
                            )
                            if transaction:
                                transactions.append(transaction)
                                processed_indices.add(i)
                                processed_indices.add(i + 1)
                                break
    
    return transactions

def extract_transaction_from_line(line: str, date_str: str, parsed_date: str, 
                                 date_span: Tuple[int, int]) -> Optional[Dict[str, Any]]:
    """
    Extract transaction details from a line that contains a date
    """
    # Find all monetary amounts in the line
    amount_pattern = r'-?£?\d+(?:,\d{3})*\.?\d{0,2}'
    amounts = []
    
    for match in re.finditer(amount_pattern, line):
        amount_str = match.group()
        # Clean and convert
        amount_str = amount_str.replace('£', '').replace(',', '')
        
        # Skip if it's part of the date
        if match.start() >= date_span[0] and match.end() <= date_span[1]:
            continue
        
        try:
            # Only include if it looks like money (has decimal or is large enough)
            amount = float(amount_str)
            if '.' in match.group() or amount > 10:  # Either has decimal or > £10
                amounts.append({
                    'value': amount,
                    'position': match.start(),
                    'original': match.group()
                })
        except ValueError:
            continue
    
    if not amounts:
        return None
    
    # Extract description (text between date and first amount, or after date)
    desc_start = date_span[1]
    desc_end = amounts[0]['position'] if amounts else len(line)
    description = line[desc_start:desc_end].strip()
    
    # Clean description
    description = re.sub(r'^\W+|\W+$', '', description)  # Remove leading/trailing non-word chars
    description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
    
    # If description is too short, try to find more text
    if len(description) < 3 and amounts:
        # Look for text after the first amount
        if len(amounts) > 1:
            alt_desc = line[amounts[0]['position'] + len(amounts[0]['original']):amounts[1]['position']]
            if len(alt_desc.strip()) > len(description):
                description = alt_desc.strip()
    
    # Categorize amounts
    transaction = {
        'date': parsed_date,
        'description': description if description else 'Transaction',
        'debit': None,
        'credit': None,
        'balance': None
    }
    
    # Logic for amount assignment
    if len(amounts) == 1:
        # Single amount - determine if debit or credit
        amt = amounts[0]['value']
        if amt < 0:
            transaction['debit'] = abs(amt)
        else:
            # Check context for debit indicators
            line_lower = line.lower()
            if any(indicator in line_lower for indicator in ['payment', 'debit', 'purchase', 'withdrawal']):
                transaction['debit'] = amt
            else:
                transaction['credit'] = amt
    
    elif len(amounts) == 2:
        # Two amounts - likely amount and balance
        amt = amounts[0]['value']
        bal = amounts[1]['value']
        
        # The larger absolute value is usually the balance
        if abs(bal) > abs(amt) * 2:  # Balance is typically much larger
            transaction['balance'] = bal
            if amt < 0:
                transaction['debit'] = abs(amt)
            else:
                transaction['credit'] = amt
        else:
            # Might be debit and credit
            if amt < 0:
                transaction['debit'] = abs(amt)
                transaction['credit'] = bal if bal > 0 else None
            else:
                transaction['debit'] = bal if bal < 0 else None
                transaction['credit'] = amt
    
    elif len(amounts) >= 3:
        # Multiple amounts - likely debit, credit, balance
        # Assume last is balance, others are debit/credit
        transaction['balance'] = amounts[-1]['value']
        
        # Process other amounts
        for amt in amounts[:-1]:
            if amt['value'] < 0:
                transaction['debit'] = abs(amt['value'])
            elif amt['value'] > 0 and transaction['credit'] is None:
                transaction['credit'] = amt['value']
    
    return transaction

def extract_table_transactions(content: str) -> List[Dict[str, Any]]:
    """
    Extract transactions assuming a table structure with consistent columns
    """
    transactions = []
    lines = content.split('\n')
    
    # Find lines that look like headers
    header_line = None
    header_idx = -1
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if ('date' in line_lower or 'transaction' in line_lower) and \
           ('amount' in line_lower or 'debit' in line_lower or 'credit' in line_lower):
            header_line = line
            header_idx = i
            break
    
    if header_idx == -1:
        return transactions
    
    # Detect column positions from header
    columns = detect_column_positions(header_line)
    if not columns:
        return transactions
    
    # Process data lines
    for line in lines[header_idx + 1:]:
        if not line.strip():
            continue
        
        # Extract values based on column positions
        values = extract_by_column_position(line, columns)
        
        # Create transaction if valid
        transaction = create_transaction_from_columns(values, columns)
        if transaction and transaction.get('date'):
            transactions.append(transaction)
    
    return transactions

def extract_block_transactions(content: str) -> List[Dict[str, Any]]:
    """
    Extract transactions from block-formatted text (common in OCR output)
    """
    transactions = []
    
    # Split by double newlines or other block separators
    blocks = re.split(r'\n\s*\n', content)
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        # Check if block contains transaction-like content
        if not re.search(r'\d{2}[/-]\d{2}', block):  # No date
            continue
        
        # Try to parse as single transaction
        lines = block.split('\n')
        
        # Look for date line
        date_line = None
        date_parsed = None
        
        for line in lines:
            date_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{2,4})', line)
            if date_match:
                date_parsed = parse_date_flexible(date_match.group(1), None)
                date_line = line
                break
        
        if not date_parsed:
            continue
        
        # Extract amounts from all lines
        amounts = []
        description_parts = []
        
        for line in lines:
            # Get amounts
            amt_matches = re.findall(r'-?£?\d+(?:,\d{3})*\.?\d{0,2}', line)
            for amt_str in amt_matches:
                clean_amt = amt_str.replace('£', '').replace(',', '')
                try:
                    amt = float(clean_amt)
                    if '.' in amt_str or amt > 10:
                        amounts.append(amt)
                except:
                    pass
            
            # Get text that might be description
            clean_line = re.sub(r'-?£?\d+(?:,\d{3})*\.?\d{0,2}', '', line).strip()
            clean_line = re.sub(r'\d{2}[/-]\d{2}[/-]\d{2,4}', '', clean_line).strip()
            if clean_line and len(clean_line) > 2:
                description_parts.append(clean_line)
        
        if amounts:
            transaction = {
                'date': date_parsed,
                'description': ' '.join(description_parts) if description_parts else 'Transaction',
                'debit': None,
                'credit': None,
                'balance': None
            }
            
            # Assign amounts
            if len(amounts) >= 1:
                if amounts[0] < 0:
                    transaction['debit'] = abs(amounts[0])
                else:
                    transaction['credit'] = amounts[0]
            
            if len(amounts) >= 2:
                transaction['balance'] = amounts[-1]
            
            transactions.append(transaction)
    
    return transactions

def detect_column_positions(header_line: str) -> Dict[str, Tuple[int, int]]:
    """
    Detect column positions from a header line
    """
    columns = {}
    header_lower = header_line.lower()
    
    # Find column headers and their positions
    patterns = {
        'date': r'(date|transaction date)',
        'description': r'(description|details|merchant|payee)',
        'debit': r'(debit|money out|out)',
        'credit': r'(credit|money in|in)',
        'balance': r'(balance|running balance)'
    }
    
    for col_name, pattern in patterns.items():
        match = re.search(pattern, header_lower)
        if match:
            columns[col_name] = match.span()
    
    return columns

def extract_by_column_position(line: str, columns: Dict[str, Tuple[int, int]]) -> Dict[str, str]:
    """
    Extract values from a line based on column positions
    """
    values = {}
    
    # Sort columns by position
    sorted_cols = sorted(columns.items(), key=lambda x: x[1][0])
    
    for i, (col_name, (start, end)) in enumerate(sorted_cols):
        # Determine the actual end position (start of next column or end of line)
        if i < len(sorted_cols) - 1:
            actual_end = sorted_cols[i + 1][1][0]
        else:
            actual_end = len(line)
        
        # Extract value
        value = line[start:actual_end].strip()
        values[col_name] = value
    
    return values

def create_transaction_from_columns(values: Dict[str, str], 
                                   columns: Dict[str, Tuple[int, int]]) -> Optional[Dict[str, Any]]:
    """
    Create a transaction from extracted column values
    """
    transaction = {
        'date': None,
        'description': None,
        'debit': None,
        'credit': None,
        'balance': None
    }
    
    # Parse date
    if 'date' in values and values['date']:
        transaction['date'] = parse_date_flexible(values['date'], None)
    
    # Set description
    if 'description' in values:
        transaction['description'] = values['description']
    
    # Parse amounts
    for amt_type in ['debit', 'credit', 'balance']:
        if amt_type in values and values[amt_type]:
            clean_val = values[amt_type].replace('£', '').replace(',', '').strip()
            if clean_val and clean_val != '-':
                try:
                    transaction[amt_type] = abs(float(clean_val))
                except:
                    pass
    
    return transaction if transaction['date'] else None

def parse_date_flexible(date_str: str, hint_format: Optional[str] = None) -> Optional[str]:
    """
    Flexible date parser that tries multiple formats
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    # If we have a hint format, try it first
    if hint_format:
        try:
            date_obj = datetime.strptime(date_str, hint_format)
            return date_obj.strftime('%Y-%m-%d')
        except:
            pass
    
    # Try common UK formats
    formats = [
        '%d/%m/%Y', '%d/%m/%y',
        '%d-%m-%Y', '%d-%m-%y',
        '%d %b %Y', '%d %b %y',
        '%d %B %Y', '%d %B %y',
        '%d%b%Y', '%d%b%y',
    ]
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            # Handle 2-digit years
            if date_obj.year < 100:
                date_obj = date_obj.replace(year=date_obj.year + 2000)
            return date_obj.strftime('%Y-%m-%d')
        except:
            continue
    
    return None

def clean_and_validate_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate the transactions DataFrame
    """
    if df.empty:
        return df
    
    # Ensure required columns
    required_cols = ['date', 'description', 'debit', 'credit', 'balance']
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    
    # Remove invalid rows
    df = df[df['date'].notna()]  # Must have a date
    
    # Clean descriptions
    df['description'] = df['description'].fillna('Transaction')
    df['description'] = df['description'].str.strip()
    df['description'] = df['description'].str.replace(r'\s+', ' ', regex=True)
    
    # Ensure numeric columns are float
    for col in ['debit', 'credit', 'balance']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Sort by date
    df = df.sort_values('date', na_position='last')
    
    # Remove duplicates (same date, description, and amounts)
    df = df.drop_duplicates(subset=['date', 'description', 'debit', 'credit'], keep='first')
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df