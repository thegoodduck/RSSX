**Decentralized Social Media Protocol Specification**

## 1. Overview
This document defines the syntax and structure of a decentralized social media protocol that uses a minimal text-based format. The protocol supports posts and comments, ensuring authenticity through RSA cryptographic signatures and a caching mechanism that defers data management to participating servers.

## 2. Data Format
Each post or comment follows a structured key-value format, separated by colons (`:`). Entries are delimited by `---` to distinguish separate posts and comments.

### 2.1 Post Structure
A post consists of the following fields:
```
ID: <unique_post_id>
Author: <username_or_public_key_identifier>
Timestamp: <unix_timestamp>
Content: <text_of_the_post>
Signature: <base64_encoded_rsa_signature>
```

#### Example Post
```
ID: 123456
Author: Alice
Timestamp: 1710873600
Content: This is my first post on the decentralized network!
Signature: BASE64_ENCODED_RSA_SIGNATURE
```

### 2.2 Comment Structure
A comment is linked to a post using the `Parent-ID` field.
```
ID: <unique_comment_id>
Parent-ID: <referenced_post_id>
Author: <username_or_public_key_identifier>
Timestamp: <unix_timestamp>
Content: <text_of_the_comment>
Signature: <base64_encoded_rsa_signature>
```

#### Example Comment
```
ID: 987654
Parent-ID: 123456
Author: Bob
Timestamp: 1710873620
Content: I agree! This protocol is awesome.
Signature: BASE64_ENCODED_RSA_SIGNATURE
```

## 3. Signature Generation
To ensure authenticity, each post or comment must be signed using RSA. The signature is generated from the following concatenated fields:
```
<ID + Author + Timestamp + Content>
```
The resulting hash is then signed using the author's private key and encoded in Base64.

## 4. Caching and Decentralization
- Servers store posts and comments temporarily but defer to client IPs for content retrieval.
- Each server logs IPs that have interacted with posts.
- Clients request missing data from the original IP of a post’s author before relying on other sources.
- This reduces centralized moderation and ensures the integrity of the content.

## 5. Future Enhancements
- Support for multimedia links.
- Reputation system based on verified authors.
- End-to-end encryption for private messages.



