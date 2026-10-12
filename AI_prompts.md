# AI Prompts — Homework 4

A record of the prompts I typed to complete each problem.

---

## Problem 2

**Prompt:**
> now for problem 2: analyze the database
> create output/harness.md. in it for now describe each table in campus_customs.db and its different categories and a sentence on why it matters for the shop or chatbot that will be created (or both)

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 3

**Prompt:**
> now for problem 3: Build the Campus Customs website
> help me build a react + vite + typescript front end for campus customs. the top should have a navbar that links to the following main pages:
> Home; Products; About Us; Log in; Create Account
> the products page should show product images from the catalogue (use image paths in .db file) w basic product info
> each product should open a single-item page w a large image on one side and full product text on the other (description, price, sizes/stock if they're available). clicking a card on the products page should take someone there
> add a chat interface to the bottom right of the site. don't worry that it's not talking to an agent yet
> finally, add a fastapi app in backend/main.py that can serve products and images

**Follow-up prompt (if needed):**
> examine the terminal and figure out why the following errors occurred
>
> stop your servers so i can run them myself. will i have to stop them everytime to rerun the commands?
>
> okay restart them
>
> please reference https://yalebulldogblue.com/ for site style
>
> sorry i only meant the colors of the site, not everything about it

**Why the first prompt didn't work:**

---

## Problem 4

**Prompt:**
> now for problem 4: create account and login
> make a normal create-account / login flow where create account has fields for first name, last name, email, password (and confirm password) AND login  has email and password fields. new accounts should be added to the users table in the .db file and protected properly. update harness.md w how authentification works. open the site to the account page so i can test to see if it works

**Follow-up prompt (if needed):**
> wait I can't login using the test account info
>
> the password is password
>
> okay now reopen the site so i can test the text

**Why the first prompt didn't work:**
The original database accounts store their password hashes without the PBKDF2 iteration count, so the new login code couldn't verify the test account until its known password revealed that those hashes use 120,000 iterations.

---

## Problem 5

**Prompt:**
> now for problem 5: PydanticAI agent backend
> now build the shop chatbot as a pydanticai agent behind fastapi. plug it into the front-end chat widget and put the api app into backend/main.py. the agent should consist of the following 4 files:
> backend/prompts/prompt.md
> backend/agent.py
> backend/tools.py
> backend/models.py
> main.py should expose a chat route so a message from the website returns a reply from the agent
> put campus customs voice and safety basics into prompt.md. start/update types in models.py for chat replies / product cards as needed
> in harness.md, note how frontend talks to fastapi and how the agent is loaded
> finally, ensure backend runs from backend/ in the following format: uvicorn main:app --reload --port 8000

**Follow-up prompt (if needed):**
> open the site so i can test the chatbot

**Why the first prompt didn't work:**

---

## Problem 6

**Prompt:**
> now for problem 6: Tools: product info and stock
> give the agent tools that allow it to look up the following info from campus_customs.db:
> product description; price; how many are in stock (by size when the customer asks). the agent should exclusively use the database; no making up information
> expand prompts.md so the agent knows to call these tools for price and stock questions. add/update return types in models.py
> finally update harness.md by listing each tool and explain which model fields were chosen for lookup fields/why

**Follow-up prompt (if needed):**
> open the site so i can test the chatbot. how should i test it?

**Why the first prompt didn't work:**

---

## Problem 7

**Prompt:**
> now for problem 7: Chat search that updates the page
> adding a new feature: when a customer asks about a type of item, the agent should search the catalogue and the website should dynamically show those matching items as product cards. this should be an api contract where the agent returns structured product matches and then the front end renders them on the website
> after the dynamic product cards are loaded by the new feature, ensure problem 3's single-item page behavior persists.
> update prompt.md and harness.md so it's clear how search results reach the page

**Follow-up prompt (if needed):**
> open the site so i can test the chatbot

**Why the first prompt didn't work:**

---

## Problem 8

**Prompt:**
> now for problem 8: Customer memory
> when a shopper is logged in, save their chat history in the .db in an appropriate table and reload it when they return. the agent should know who is chatting w them (name/email) so add that to agent deps and tools the agent can call. also pass enough page context to the the agent that if someone is on a product page and asks a question about a product (e.g., do you have that in blue?), the agent knows what they're talking about.
> guests (not logged in users) can still chat, but history only needs to be persistent for logged-in users
> in harness.md document how chat user history is stored, what customer fields the agent sees, how page context is passed

**Follow-up prompt (if needed):**
> open the site so i can test the chatbot

**Why the first prompt didn't work:**

---

## Problem 9

**Prompt:**
> now for problem 9: Usability improvements
> make the following frontend changes to the website:
> add a related products section for each product. for example, if i clicked on a shirt, i should also be able to see similar shirts
> also have noticed that some titles aren't formatted correctly. for example, "benjamin franklin 1/4 Zip" is "benjamin franklin 1 4 zip" fix that
> also add a filter function so you can filter by size, color, price, etc
>
> also for backend changes:
> gauge which model the agent is using whenever someone chats with it to ensure it's the cheapest model
> add additional safety features so that user info is secure
> finally create output/usability.md where each of the changes i asked for is listed and why it helps either a customer or the business

**Follow-up prompt (if needed):**
> what do you mean the test account was thrown away?
>
> open the site so i can test the changes

**Why the first prompt didn't work:**

---

## Problem 10

**Prompt:**
> now for problem 10: Style the website
> i want to make the website look cooler and more yale-themed. add dan the dog sprites where feasible. make the background include logos of the different residential colleges/professional schools
> also write output/design.md, a log of what changes i asked for and why they should help people stay around longer. don't make it too long

**Follow-up prompt (if needed):**
> open the site so i can test the changes

**Why the first prompt didn't work:**

---

## Problem 11

**Prompt:**
> now for problem 11: Site testing (app check)
> test the live site and document it in output/app_check.html (a page that can be double-clicked to open)
> include clear screenshots and short captions for:
>
> 1. chat checking inventory level of an item (honest stock/price from .db)
> 2. the dynamic search-result cards appearing after a category question
> 3. one of the usability features i added in problem 9
>
> make the html easy to grade by adding a heading for each check, screenshots, and 1-2 sentences on what the screenshot proves. put screenshot images in output/app_check_images/ and link them from app_check.html w relative paths (e.g., app_check_images/inventory.png)

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 12

**Prompt:**
> now for problem 12: Audit trail, safety, finish harnesses
> make an append-only output/audit_trail.json of agent-loop activity that does not wipe between runs. do something similar to what you did in Homework 3
> also add safety rules that protect privacy, disallows the chatbot from unduly influencing others, and other prominent things the big AI labs take seriously. don't make it too wordy and add it all to prompt.md
> finally, finish harness.md so it's apparent how the system works. add the model fields in models.py and why they were chosen; tools and abilities; safety rules; and specs (loop limits, result caps, models, how to run front + back)

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---

## Problem 13

**Prompt:**
> finally, for Problem 13: Push to GitHub and submit the URL
> put everything about this assignment (except the .env, campus_customs.db, or product images--use .gitignore for these) in a folder called hw4 (this will be an organized copy of @Homeworks/Homework-4) and push it to a public GitHub repository under my account. there ahould also be a readme.md that explains how to run the front end and back end after placing the data pack
> in terms of organization, ai_prompts, requirements, .env.example, .gitignore, readme, and the frontend/ , backend/ , and output/ folders should ALL be in the hw4/ main folder. the backend/ folder will have the main, agent, models, and tools py files AND the prompts/ folder (which contains prompt.md). the output/ folder will have harness, design, usability, app_check, app_check_images, and audit_trail in it. other than than, no need to change what's already in the folders
> is anything confusing?

**Follow-up prompt (if needed):**
> 

**Why the first prompt didn't work:**

---
