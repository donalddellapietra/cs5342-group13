"""Implementation of automated moderator"""

from typing import List
from atproto import Client
import pandas as pd
import os
import requests
from .label import post_from_url
from perception import hashers


T_AND_S_LABEL = "t-and-s"
DOG_LABEL = "dog"
THRESH = 0.3

class AutomatedLabeler:
    """Automated labeler implementation"""

    def __init__(self, client: Client, input_dir):
        self.client = client
        self.input_dir = input_dir
        self.t_and_s_words = self.load_t_and_s_words()
        self.t_and_s_domains = self.load_t_and_s_domains()
        self.news_domains = self.load_news_domains()
        self.dog_hashes = self.load_dog_hashes()

    def load_t_and_s_words(self) -> List[str]:
        """Load T&S words from CSV"""
        file_path = os.path.join(self.input_dir, 't-and-s-words.csv')
        return pd.read_csv(file_path)['Word'].str.lower().tolist()

    def load_t_and_s_domains(self) -> List[str]:
        """Load T&S domains from CSV"""
        file_path = os.path.join(self.input_dir, 't-and-s-domains.csv')
        return pd.read_csv(file_path)['Domain'].str.lower().tolist()

    def load_news_domains(self) -> dict:
        """Load news domains and their corresponding labels from CSV"""
        file_path = os.path.join(self.input_dir, 'news-domains.csv')
        df = pd.read_csv(file_path)
        return dict(zip(df['Domain'].str.lower(), df['Source']))

    def load_dog_hashes(self) -> List[str]:
        """Load perceptual hashes for dog images"""
        dog_images_dir = os.path.join(self.input_dir, 'dog-list-images')
        dog_hashes = []
        hasher = hashers.PHash()
        for image_file in os.listdir(dog_images_dir):
            image_path = os.path.join(dog_images_dir, image_file)
            dog_hashes.append(hasher.compute(image_path))
        return dog_hashes

    def moderate_post(self, url: str) -> List[str]:
        """
        Apply moderation to the post specified by the given url
        """
        post_content, image_urls = self.fetch_post_content(url)
        labels = set()

        # T&S words and domains
        if any(word in post_content for word in self.t_and_s_words) or \
           any(domain in post_content for domain in self.t_and_s_domains):
            labels.add(T_AND_S_LABEL)

        # News domains
        for domain, label in self.news_domains.items():
            if domain in post_content:
                labels.add(label)

        # Dog images
        for image_url in image_urls:
            if self.is_dog_image(image_url):
                labels.add(DOG_LABEL)
                break

        return list(labels)

    def is_dog_image(self, image_url: str) -> bool:
        """Check if the image at the given URL matches any dog image"""
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            with open('temp_image.jpg', 'wb') as f:
                f.write(response.content)
            hasher = hashers.PHash()
            image_hash = hasher.compute('temp_image.jpg')
            for dog_hash in self.dog_hashes:
                if hasher.compute_distance(image_hash, dog_hash) <= THRESH:
                    return True
        except Exception as e:
            print(f"Error processing image {image_url}: {e}")
        return False

    def fetch_post_content(self, url: str) -> str:
        """Fetch the content of the post from the given URL"""
        try:
            post = post_from_url(self.client, url)
            post_content = post.value.text
            image_urls = []
            if post.value.embed and post.value.embed.images:
                for image in post.value.embed.images:
                    # remove the 'at://' prefix from the URI and keep only the first part
                    uri = post.uri.replace("at://", "").split('/')[0]
                    image_urls.append(f"https://cdn.bsky.app/img/feed_fullsize/plain/{uri}/{image.image.ref.link}")
            return post_content, image_urls
        except Exception as e:
            print(f"Error fetching post content from {url}: {e}")
            return "", []