<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/Cyclip/Kularity/">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Kularity</h3>

  <p align="center">
    An extensive reddit comment scraper
    <br />
    <a href="https://github.com/Cyclip/Kularity"><strong>Explore the docs »</strong></a>
    <br />
    <br />
  </p>
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#information">Information</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

[![Kularity screenshot][product-screenshot]](https://github.com/Cyclip/Kularity/)

Kularity provides a simplistic, customisable and straightforward way to scrape reddit to retrieve comments and their scores. Data may be used for machine learning datasets, statistics or other tasks. It uses an algorithm which scrapes for comments specifically ignoring inactive users while continually looking for more related users to use. Each scrape is split into layers.

### Algorithm
**Creation stage:**
* Get posts from a starting point and their posters
* For each post, collect comments and their users
* Build next layer of users
* Start layer process from first layer

**Layer processing stage:**
This stage is creates 1 layer of data.
* For each username:
	* Get all comments + scores made by users
	* For each comment, get poster username
	* Add submission ID poster to next layer
* Repeat process if there are remaining layers

### Built With

This section should list any major frameworks that you built your project using. Leave any add-ons/plugins for the acknowledgements section. Here are a few examples.
* [Python](https://www.python.org/)
* [Praw](https://praw.readthedocs.io/en/latest/)


<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

You will need to install some Python modules for this to work.
```
python -m pip install -r requirements.txt
```

You also need a client ID, client secret & user agent.
They should be stored in `function/.env`. A typical .env file would look like this:
```
client_id="wai98jtujsorsomething"
client_secret="jdwa8a9hrrui8jawd89jua09aju"
user_agent="windows:myscraper:1.0.0 (by u/user)"
```

### Installation

1. Get a client ID and secret using [these steps](https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps)
2. Insert the client id, secret and your own user agent into `functions/.env`
3. Clone the repo
   ```sh
   git clone https://github.com/Cyclip/Kularity.git
   ```
4. Run the test (`debug.bat` or `info.bat`)
5. Collect results at `test/dump.db`



<!-- USAGE EXAMPLES -->
## Usage

Use this space to show useful examples of how a project can be used. Additional screenshots, code examples and demos work well in this space. You may also link to more resources.

_For more examples, please refer to the [Documentation](https://example.com)_


<!-- LICENSE -->
## License

Distributed under GNU General Public License v3.0. See `LICENSE` for more information.

<!-- INFORMATION -->
# Information

## Arguments
`python main.py -h` for a shortened version

### startingPostLimit
**Default**: `100` (capped at 100)
Number of initial posts to start off with.

## startingSubreddit
**Default**: `all`
Scrape `startingPostLimit` posts from this subreddit at the start.
This does not mean all posts scraped will be from here, unless stated in `restrictSubs`

## startingSort
**Default**: `hot`
Sorting to use when scraping the initial posts

## postCommentLimit
**Default**: `5000`
Maximum number of comments to scrape from each of the initial posts.
A higher value means more comments and more users to start scraping from.

## userCommentLimit
**Default**: `1000` (capped at 1000)
Maximum number of comments to scrape from a single user.

## userLimit
**Default**: `None`
The maximum number of users to scrape from in *per layer*

## submissionLimit
**Default**: `15`
Maximum number of submissions to scrape from under a user's comments.
For example when scraping a user's comments, the first 15 comments will have the submissions retrieved as well (the username of the submission poster specifically).
This is very heavy on performance.

## verbose
More verbose logging (for debugging or nice to look at)

## fileLogging
Log to `build/log.log` as well as the console

## layers
**Default**: `3`
Maximum number of layers to process excluding creation.

## dir
**Default**: `dump`
Directory to dump all data in.

## normalize
**nargs**: 2 (`int`, `int`)
**Example**: `--normalize -5 100`
Normalize the score between a given range to output from 0 to 1.

## noInput
Disable all possible inputs

## formatJSON
Store the data in `dump.json` as well as `dump.db`

## blockUsers
**Default**: `None`
**Example**: `--blockUsers users.txt`
Argument should be a file path. File should follow this format:
```
user1
user2
...
```

## blockSubreddits
**Default**: `None`
**Example**: `--blockSubreddits subreddits.txt`
Argument should be a file path. File should follow this format:
```
subreddit1
subreddit2
...
```

## blockNSFW
Block all NSFW profiles/subreddits. This may significantly decrease the number of comments scraped.

## minScore
**Default**: `-10000000`
Minimum comment score required


## maxScore
**Default**: `10000000`
Maximum comment score required

## minTime
**Example**: `--minTime "01/01/2021 00:00:00"`
All comments/submissions must be made from this value (d/m/y H:M:S)

## restrictSubs
**Default**: `None`
**Exmaple**: `--restrictSubs subreddits.txt`
Restrict all comments and posts to be in that subreddit. Not intended for this algorithm but it's an option nonetheless.

## notify
Play a notification sound when scraping is complete.

--

Sound effects obtained from https://www.zapsplat.com

[product-screenshot]: images/example.png