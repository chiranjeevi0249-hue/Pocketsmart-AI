from flask import Flask, render_template, request, redirect, url_for, session
from google import genai
from dotenv import load_dotenv
import os
import urllib.parse

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Flask secret key
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "pocketsmart-dev-secret-key"
)

# Connect to Gemini
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# -----------------------------
# LOGIN
# -----------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "admin" and password == "admin123":

            session["user"] = username
            session["history"] = []

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# -----------------------------
# HOME PAGE
# -----------------------------

@app.route("/")
def home():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        history=session.get("history", [])
    )


# -----------------------------
# SHOPPING LINKS
# -----------------------------

def generate_shopping_links(category, preferences):

    search_text = urllib.parse.quote_plus(preferences)

    if category == "Home Interior Planning":

        return [
            {
                "name": "Amazon",
                "url": f"https://www.amazon.in/s?k={search_text}"
            },
            {
                "name": "IKEA",
                "url": f"https://www.ikea.com/in/en/search/?q={search_text}"
            },
            {
                "name": "Flipkart",
                "url": f"https://www.flipkart.com/search?q={search_text}"
            }
        ]

    elif category == "Party Budget Planning":

        return [
            {
                "name": "Amazon",
                "url": f"https://www.amazon.in/s?k={search_text}"
            },
            {
                "name": "Swiggy",
                "url": "https://www.swiggy.com/"
            },
            {
                "name": "Zomato",
                "url": "https://www.zomato.com/"
            }
        ]

    elif category == "Jewelry Selection":

        return [
            {
                "name": "Amazon",
                "url": f"https://www.amazon.in/s?k={search_text}"
            },
            {
                "name": "Flipkart",
                "url": f"https://www.flipkart.com/search?q={search_text}"
            },
            {
                "name": "Myntra",
                "url": f"https://www.myntra.com/{search_text}"
            }
        ]

    return []


# -----------------------------
# AI RECOMMENDATION
# -----------------------------

@app.route("/recommend", methods=["POST"])
def recommend():

    if "user" not in session:
        return redirect(url_for("login"))

    # Get user inputs
    category = request.form.get("category", "").strip()
    budget = request.form.get("budget", "").strip()
    preferences = request.form.get("preferences", "").strip()

    # Get uploaded image
    jewelry_image = request.files.get("jewelry_image")

    # -----------------------------
    # INPUT VALIDATION
    # -----------------------------

    if not category or not budget or not preferences:
        return "Please fill in all required fields.", 400

    try:
        budget_value = float(budget)

    except ValueError:
        return "Please enter a valid budget amount.", 400

    if budget_value <= 0:
        return "Budget must be greater than zero.", 400


    # -----------------------------
    # IMAGE VALIDATION
    # -----------------------------

    if jewelry_image and jewelry_image.filename:

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        }

        filename = jewelry_image.filename.lower()

        if not any(filename.endswith(ext) for ext in allowed_extensions):

            return "Please upload a JPG, JPEG, PNG, or WEBP image.", 400


    # -----------------------------
    # PROMPT
    # -----------------------------

    prompt = f"""
You are PocketSmart AI, an intelligent budgeting and recommendation assistant.

The user wants help with:
{category}

User budget:
₹{budget_value:,.2f}

User preferences and requirements:
{preferences}
"""

    # If jewelry image exists
    if category == "Jewelry Selection" and jewelry_image and jewelry_image.filename:

        prompt += """

The user has uploaded an outfit or jewelry-related image.

Analyze the uploaded image and provide suitable jewelry recommendations.

Consider:

1. Outfit style
2. Outfit color
3. Overall appearance
4. Suitable jewelry type
5. Suitable jewelry color
6. Suitable jewelry style
7. Approximate budget

Keep the recommendations practical and within the user's budget.
"""

    else:

        prompt += """

Create a practical personalized recommendation based on the user's
category, budget and preferences.
"""


    prompt += """

Follow these rules:

1. Create a realistic budget allocation.
2. Keep total estimated spending within the user's budget.
3. Give suitable recommendations.
4. Provide estimated costs.
5. Clearly show the total estimated cost.
6. Clearly show the remaining budget.
7. Give useful money-saving suggestions.
8. Do not exceed the user's budget.
9. Keep the response simple and easy to understand.

Use this format:

POCKETSMART AI RECOMMENDATION

CATEGORY
[Category]

BUDGET
[Budget]

BUDGET ALLOCATION
- Category 1: Amount
- Category 2: Amount
- Category 3: Amount

RECOMMENDATIONS
1. Recommendation - Estimated Cost
2. Recommendation - Estimated Cost
3. Recommendation - Estimated Cost

TOTAL ESTIMATED COST
[Total]

REMAINING BUDGET
[Remaining amount]

MONEY-SAVING TIPS
- Tip 1
- Tip 2
- Tip 3
"""


    # -----------------------------
    # GEMINI AI
    # -----------------------------

    try:

        # Normal recommendation
        if not (
            category == "Jewelry Selection"
            and jewelry_image
            and jewelry_image.filename
        ):

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

        # Image-based recommendation
        else:

            image_bytes = jewelry_image.read()

            image_part = genai.types.Part.from_bytes(
                data=image_bytes,
                mime_type=jewelry_image.mimetype
            )

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[
                    prompt,
                    image_part
                ]
            )

        result = response.text

    except Exception as e:

        return f"Gemini API error: {str(e)}", 500


    # -----------------------------
    # SHOPPING LINKS
    # -----------------------------

    shopping_links = generate_shopping_links(
        category,
        preferences
    )


    # -----------------------------
    # SAVE HISTORY
    # -----------------------------

    history = session.get("history", [])

    history.append({
        "category": category,
        "budget": budget_value,
        "preferences": preferences
    })

    # Keep latest 5
    session["history"] = history[-5:]


    # -----------------------------
    # DISPLAY RESULT
    # -----------------------------

    return render_template(
        "result.html",
        result=result,
        category=category,
        budget=budget_value,
        shopping_links=shopping_links
    )


# -----------------------------
# START FLASK
# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)