"""Script to label posts related to personal medical issues on Bluesky"""

from atproto import Client, models
import os
from dotenv import load_dotenv
import openai
import pandas as pd
from label import did_from_handle, label_post

load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

class PolicyProposalLabeler:
    """
    Labeler for policy proposals on Bluesky
    """
    def __init__(self, client: Client):
        self.client = client
        self.keywords = [
            "anxiety", "depression", "stress", "therapy", "mental health",
            "cancer", "diabetes", "chronic pain", "illness", "diagnosis",
            "medication", "treatment", "symptoms", "doctor", "hospital"
        ]

    def fetch_and_label_posts(self):
        """
        Fetch and label posts containing any of the keywords
        """
        labeled_posts = []
        saved_posts = []

        # Search for posts containing any of the keywords
        for keyword in self.keywords:
            params = models.app.bsky.feed.search_posts.Params(q=keyword, limit=8, sort='latest')
            response = self.client.app.bsky.feed.search_posts(params)

            # Process and label the posts
            for post in response.posts:
                post_content = post.record.text.lower()
                author = post.author.display_name
                timestamp = post.record.created_at
                label = self.classify_post(post_content)
                true_label = label
                action_taken = ""
                # Skip labeling if the category is "Other"
                if label == "Other":
                    print(f"Post by {author} at {timestamp}: {post_content} - No label applied")
                    true_label = ""
                

                # Send a support message if the label is "Risk of Harm to Self or Others"
                if label == "Risk of Harm to Self":
                    self.send_support_message(author)
                    action_taken = "Message sent"
                    # do not label this post
                    true_label = ""
                
                if label == "Risk of Harm to Others":
                    self.flag_post(post.uri)
                    action_taken = "Manual review"
                    # do not label this post
                    true_label = ""

                print(f"Post by {author} at {timestamp}: {post_content} - Label: {label}")


                labeled_posts.append([post.uri, [true_label]])
                saved_posts.append({"uri": post.uri, "author": author, "timestamp": timestamp, "content": post_content, "action_taken": action_taken, "label": true_label})

        return labeled_posts, saved_posts

                

    def classify_post(self, post_content: str) -> str:
        """
        Classify the post into one of the categories using GPT-4o-mini
        """
        # the category Personal Health Disclosure serves as a trigger warning, since it is a sensitive topic
        prompt = f"""
        Classify the following post into one of the following categories: 
        • Personal Health Disclosure
        • Risk of Harm to Self
        • Risk of Harm to Others
        • Health Advice
        • Medical News
        • Satire/Parody
        • Potential Misinformation
        • Medical Question
        • Other

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
        """
        Send a support message to the author
        """
        support_message = """
        Hi, this is an automated bot. I noticed your post might indicate distress. 
        
        If you need help, please contact one of these national support hotlines:
        
        - National Suicide Prevention Lifeline: 1-800-273-8255
        - Crisis Text Line: Text HOME to 741741
        - SAMHSA's National Helpline: 1-800-662-4357
        
        Your well-being matters. Please reach out if you need support.
        """
        
        print(f"Sending support message to {author}:\n{support_message}")
        # something like this (not actually sending)
        # self.client.send_message(author, support_message)

    def flag_post(self, uri: str):
        """
        Flag the post for manual review (we check our own inbox for these and report them to Bluesky)
        """
        print(f"Flagging post {uri}")
        message_content = f"Manual review needed for post: {uri}"
        # send a message to our own inbox (not actually sending)
        # self.client.send_message(self.client.me.did, message_content)



def save_labeled_posts_to_csv(labeled_posts, output_file='labeled_posts.csv'):
    """
    Save the labeled posts to a CSV file
    """
    df = pd.DataFrame(labeled_posts)
    df.to_csv(output_file, index=False)
    print(f"Labeled posts saved to {output_file}")


def main():
    """Main function"""
    client = Client()
    client.login(USERNAME, PW)
    labeler = PolicyProposalLabeler(client)
    labeled_posts, saved_posts = labeler.fetch_and_label_posts()

    ### Note: uncomment the following code to actually label the posts ###
    # labeler_client = None
    # did = did_from_handle(USERNAME)
    # labeler_client = client.with_proxy("atproto_labeler", did)
    # for post in labeled_posts:
    #     label_post(client, labeler_client, post[0], post[1])


    # Save the labeled posts to a CSV file
    save_labeled_posts_to_csv(saved_posts)




if __name__ == "__main__":
    main()