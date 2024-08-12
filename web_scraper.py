from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from datetime import datetime
import dateparser
from dateutil.relativedelta import relativedelta

# Initialize WebDriver (example for Chrome)
driver = webdriver.Chrome()

# Access the specific query page
driver.get("https://customer.cradlepoint.com/s/topic/0TO38000000Q3MGGA0/security")

queries = []
query_timestamps = []
responses = []
response_timestamps = []
timestamp_diffs = []

def parse_timestamp(timestamp_str):
    return dateparser.parse(timestamp_str)

def calculate_relative_time(query_time):
    now = datetime.now()
    delta = relativedelta(now, query_time)
    if delta.years > 0:
        return f"{delta.years} years ago"
    elif delta.months > 0:
        return f"{delta.months} months ago"
    elif delta.days > 0:
        return f"{delta.days} days ago"
    elif delta.hours > 0:
        return f"{delta.hours} hours ago"
    elif delta.minutes > 0:
        return f"{delta.minutes} minutes ago"
    else:
        return "just now"

def click_view_more():
    while True:
        try:
            view_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'View More')]")
            view_more_button.click()
            time.sleep(3)  # Wait for content to load
        except Exception as e:
            print("No more 'View More' buttons found.")
            break

def load_all_queries():
    # Wait for the page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "cuf-feedElementIterationItem"))
    )

    # Click "View More" button until all queries are loaded
    while True:
        try:
            view_more_button = driver.find_element(By.XPATH, "//button[contains(text(), 'View More')]")
            view_more_button.click()
            time.sleep(2)  # Wait for new content to load
        except:
            break

    # Find all query elements
    query_elements = driver.find_elements(By.CLASS_NAME, "cuf-feedElementIterationItem")
    return query_elements

def process_query(element):
    try:
        # Locate the question text within the query container
        question_container = element.find_element(By.CLASS_NAME, "cuf-questionTitle")
        question_text = question_container.find_element(By.CLASS_NAME, "uiOutputText").text
        if question_text:
            print(f"Query: {question_text}")  # Print text to verify
            queries.append(question_text)

        # Extract the query timestamp
        try:
            query_timestamp_element = element.find_element(By.CLASS_NAME, "cuf-timestamp")
            query_timestamp_text = query_timestamp_element.text
            print(f"Query Timestamp: {query_timestamp_text}")  # Print text to verify
            query_timestamp = parse_timestamp(query_timestamp_text)
            query_timestamps.append(query_timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            print(f"Error extracting query timestamp: {e}")
            query_timestamps.append("N/A")
            query_timestamp = datetime.now()

        # Click on the question link to open the new tab
        question_link = element.find_element(By.CLASS_NAME, "cuf-feedElement-wrap").get_attribute("href")
        driver.execute_script("window.open(arguments[0]);", question_link)

        # Switch to the new tab
        driver.switch_to.window(driver.window_handles[1])

        try:
            # Wait for the answer to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "cuf-feedback"))
            )

            # Find the main response container
            response_container = driver.find_element(By.CLASS_NAME, "cuf-feedback")

            # Extract all comment elements within the response container
            comment_elements = response_container.find_elements(By.CLASS_NAME, "cuf-commentLi")

            if not comment_elements:
                responses.append("No response")
                response_timestamps.append("N/A")
                timestamp_diffs.append("N/A")
            else:
                response_text = ""
                for idx, comment in enumerate(comment_elements):
                    try:
                        response_type = "Unknown Response"  # Initialize response_type
                        
                        # Find the content within each comment
                        content_container = comment.find_element(By.CLASS_NAME, "cuf-feedBodyText")
                        print(f"Found content container: {content_container}")  # Logging

                        # Extract the username and determine if it's a Cradlepoint response or Customer response
                        try:
                            additional_label_element = comment.find_element(By.XPATH, ".//span[@class='cuf-entityAdditionalLabel uiOutputText']")
                            additional_label_text = additional_label_element.text
                            response_type = "Cradlepoint Response" if "Cradlepoint" in additional_label_text else "Customer Response"
                        except Exception as e:
                            print(f"Error extracting additional label: {e}")

                        # Extract the answer timestamp
                        try:
                            response_timestamp_element = comment.find_element(By.CLASS_NAME, "cuf-commentAge")
                            response_timestamp_text = response_timestamp_element.text
                            formatted_timestamp = response_timestamp_text
                            print(f"Response Timestamp: {formatted_timestamp}")  # Print text to verify
                            response_timestamps.append(formatted_timestamp)

                            # Calculate the difference between query and response timestamps
                            response_time = dateparser.parse(response_timestamp_text, settings={'RELATIVE_BASE': query_timestamp})
                            if response_time:
                                delta = relativedelta(query_timestamp, response_time)
                                time_diff = format_timedelta(delta)
                            else:
                                time_diff = "N/A"
                            timestamp_diffs.append(time_diff)
                        except Exception as e:
                            print(f"Error extracting response timestamp: {e}")
                            response_timestamps.append("N/A")
                            timestamp_diffs.append("N/A")

                        # Check if there is an "Expand Post" link and click it if present
                        try:
                            expand_link = content_container.find_element(By.XPATH, ".//a[contains(@class, 'cuf-more') and not(contains(@class, 'hidden'))]")
                            if expand_link:
                                expand_link.click()
                                time.sleep(1)  # Wait for content to expand
                                print("Clicked 'Expand Post' link")  # Logging
                        except:
                            print("No 'Expand Post' link found")  # Logging
                            pass

                        # Extract the response text
                        response_inner_container = content_container.find_element(By.CLASS_NAME, "feedBodyInner")
                        response_elements = response_inner_container.find_elements(By.XPATH, ".//span[@class='uiOutputText']")
                        response_texts = [elem.text for elem in response_elements if elem.text.strip()]
                        if response_texts:
                            response_text += f"{response_type} {idx+1}: " + " ".join(response_texts) + " "

                    except Exception as e:
                        print(f"Error extracting response: {e}")
                        response_text += f"{response_type} {idx+1}: No response "

                responses.append(response_text.strip())

        except Exception as e:
            print(f"Error extracting response: {e}")
            responses.append("No response")
            response_timestamps.append("N/A")
            timestamp_diffs.append("N/A")

        # Close the new tab and switch back to the original tab
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    except Exception as e:
        print(f"Error processing query: {e}")
        queries.append("Error loading query")
        responses.append("Error loading response")
        query_timestamps.append("N/A")
        response_timestamps.append("N/A")
        timestamp_diffs.append("N/A")

try:
    # Step 1: Load all queries by clicking "View More" until no more buttons are found
    query_elements = load_all_queries()

    # Step 2: Process each query one by one (limited to the first 15 for testing)
    for element in query_elements[:15]:
        process_query(element)

except Exception as e:
    print(f"Error during execution: {e}")

finally:
    driver.quit()

# Ensure all lists are of the same length
max_length = max(len(queries), len(query_timestamps), len(responses), len(response_timestamps), len(timestamp_diffs))
queries.extend(["N/A"] * (max_length - len(queries)))
query_timestamps.extend(["N/A"] * (max_length - len(query_timestamps)))
responses.extend(["N/A"] * (max_length - len(responses)))
response_timestamps.extend(["N/A"] * (max_length - len(response_timestamps)))
timestamp_diffs.extend(["N/A"] * (max_length - len(timestamp_diffs)))

# Save data to Excel
data = {
    "Query": queries,
    "Query Timestamp": query_timestamps,
    "Response": responses,
    "Response Timestamp": response_timestamps,
    "Timestamp Difference": timestamp_diffs
}

df = pd.DataFrame(data)
df.to_excel("Updated_Cradlepoint_Forum_Queries_Test.xlsx", index=False)
