import sys
import os
import email
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer


def read_raw_blocks(mbox_file_path):
    """
    Helper generator that reads the file line-by-line and groups them into 
    individual raw email text blocks. This guarantees the last message is flushed.
    """
    with open(mbox_file_path, 'r', encoding='utf-8', errors='replace') as f:
        current_message_lines = []
        for line in f:
            if line.startswith('From '):
                if current_message_lines:
                    yield "".join(current_message_lines)
                    current_message_lines = []
            current_message_lines.append(line)
        if current_message_lines:
            yield "".join(current_message_lines)

def extract_mbox_fields(mbox_file_path):
    """
    Parses an mbox file block-by-block, extracting fields through a single yield layout.
    """
    if not os.path.exists(mbox_file_path):
        print(f"Error: The file '{mbox_file_path}' does not exist.")
        return

    # Stream text blocks from our helper generator
    for raw_email_text in read_raw_blocks(mbox_file_path):
        # Using the standard parser guarantees custom X-Headers are preserved
        message = email.message_from_string(raw_email_text)
        
        message_id = message.get('Message-ID')
        original_sender = message.get('From')
        to_field = message.get('To')
        date_field = message.get('Date')
        mailing_list = message.get('Mailing-list')
        subject = message.get('Subject')
        gmail_labels = message.get('X-Gmail-Labels')

        body_bytes = 0
        body_bytes += get_message_body_size(message)
        body_size_kb = int(body_bytes / 1024)

        labels_list = gmail_labels.split(',')
        
        yield {
            "Message-ID": message_id,
            "From": original_sender,
            "To": to_field,
            "Date": date_field,
            "List": mailing_list,
            "Subject": subject,
            "Labels": gmail_labels,
            "MessageBodySize": body_size_kb,
            "IsInTrash": get_is_message_in_trash_flag(labels_list),
            "IsUnread": get_is_message_unread_flag(labels_list)
        }

def get_message_body_size(message):
    size = 0
    
    if message.is_multipart():
        for part in message.walk():
            if not part.is_multipart():
                size += len(part.get_payload(decode=True))
    else:
        size = len(message.get_payload(decode=True))
    
    return size
                
def get_message_topic(message):
    topic = "No Body Content"
    
def get_is_message_in_trash_flag(labels_list):
    if 'Trash' in labels_list:
        return 1
    else:
        return 0
        

def get_is_message_unread_flag(labels_list):
    if 'Unread' in labels_list:
        return 1
    else:
        return 0


    if get_message_body_size(message) > 0:
        if message.is_multipart():
            topic = "Message with attachments"
        else:
            try:
                topics, _ = topic_model.fit_transform(message)

                # Get the primary keyword descriptor for the assigned cluster
                topic_info = topic_model.get_topic(topics[0])
                topic = topic_info[0][0] if topic_info else "General Text"
            except Exception:
                raise RuntimeError("Analysis Error")

    return topic
    
    
if __name__ == "__main__":
    MBOX_PATH = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Error: Please provide the path to your mbox file as a command line argument.")
    
    # Initialize the embedding model and BERTopic model
    ##embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    ##topic_model = BERTopic(embedding_model=embedding_model)
    
    # for email_data in extract_mbox_fields(MBOX_PATH):            
    #     print("-" * 50)
    #     print(f"Message-ID: {email_data['Message-ID']}")
    #     print(f"Subject:    {email_data['Subject']}")
    #     print(f"From:       {email_data['From']}")
    #     print(f"To:         {email_data['To']}")
    #     print(f"Date:       {email_data['Date']}")        
    #     print(f"List:       {email_data['List']}")
    #     print(f"Labels:     {email_data['Labels']}")
    #     print(f"Body Size:  {email_data['MessageBodySize']} KB")
    #     print(f"IsUnread:   {email_data['IsUnread']}")
    #     print(f"IsInTrash:  {email_data['IsInTrash']}")
   
    messages = list(extract_mbox_fields(MBOX_PATH))   
    df_messages = pd.DataFrame(messages)
   
    print(f"Successfully loaded {len(df_messages)} rows")
   
    # Clean and convert the 'Date' field to actual datetime objects
    # errors='coerce' turns unparseable dates into NaT (Not a Time) instead of crashing
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', utc=True)
    
    # Group by sender and sort by Date within each group
    df_sorted = df.sort_values(by=['From', 'Date'], ascending=[True, True])

    df_sorted['TimeSinceLastMessage'] = (
        df_sorted.groupby('From', sort=False)['Date']
        .diff()
        .dt.total_seconds()
        .fillna(0)           # The oldest message has no previous row, so set NaN to 0
        .astype(int)
    )

    # Display the new feature output
    print("\nDataFrame with TimeSinceLastMessage Feature:")
    print(df_sorted[['X-Original-Sender', 'Date', 'TimeSinceLastMessage', 'Subject']].head(10))    
