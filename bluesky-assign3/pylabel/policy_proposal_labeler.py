"""Script to label posts related to personal medical issues on Bluesky"""

from atproto import Client, models
import os
from dotenv import load_dotenv
import openai

load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

class PolicyProposalLabeler:
    def __init__(self, client: Client):
        self.client = client
        self.keywords = [
            "anxiety", "depression", "stress", "therapy", "mental health",
            "cancer", "diabetes", "chronic pain", "illness", "diagnosis",
            "medication", "treatment", "symptoms", "doctor", "hospital"
        ]

    def fetch_and_label_posts(self):
        labeled_posts = []

        # Search for posts containing any of the keywords
        for keyword in self.keywords:
            params = models.app.bsky.feed.search_posts.Params(q=keyword, limit=10, sort='latest')
            response = self.client.app.bsky.feed.search_posts(params)

            # Process and label the posts
            for post in response.posts:
                post_content = post.record.text.lower()
                author = post.author.display_name
                timestamp = post.record.created_at
                label = self.classify_post(post_content)
                
                # Skip labeling if the category is "Other"
                if label == "Other":
                    print(f"Post by {author} at {timestamp}: {post_content} - No label applied")
                    continue
                
                print(f"Post by {author} at {timestamp}: {post_content} - Label: {label}")

                # Send a support message if the label is "Risk of Harm to Self or Others"
                if label == "Risk of Harm to Self or Others":
                    self.send_support_message(author)
                    # do not label this post
                    continue

                labeled_posts.append([post.uri, [label]])

        return labeled_posts

                

    def classify_post(self, post_content: str) -> str:
        prompt = f"""
        Classify the following post into one of the following categories: 
        1. Personal Health Disclosure
        2. Risk of Harm to Self or Others
        3. Health Advice
        4. Medical News
        5. Potentially Misleading
        6. Medically Related Story
        7. Medical Question
        8. Other

        Post: "{post_content}"

        Output only the category name.
        """
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies posts into predefined categories."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            n=1,
            temperature=0
        )
        return response.choices[0].message.content.strip()


    def send_support_message(self, author: str):
        support_message = """
        Hi, this is an automated bot. I noticed your post might indicate distress. 
        
        If you need help, please contact one of these national support hotlines:
        
        - National Suicide Prevention Lifeline: 1-800-273-8255
        - Crisis Text Line: Text HOME to 741741
        - SAMHSA's National Helpline: 1-800-662-4357
        
        Your well-being matters. Please reach out if you need support.
        """
        
        print(f"Sending support message to {author}:\n{support_message}")
        # something like this:
        # self.client.send_message(author, support_message)

def main():
    """Main function"""
    client = Client()
    client.login(USERNAME, PW)
    labeler = PolicyProposalLabeler(client)
    labeled_posts = labeler.fetch_and_label_posts()
    print(labeled_posts)

if __name__ == "__main__":
    main()