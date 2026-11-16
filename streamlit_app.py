import os
import json
import time
import base64
import streamlit as st
import folium
from streamlit_folium import st_folium
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# --- PAGE CONFIG & DARK VELVET + GOLD THEME ---
st.set_page_config(
    page_title="NestMate AI — Smart Area Flatmate Finder",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
  }
  .stApp {
    background: radial-gradient(circle at top left, #1c1326 0%, #0d0a14 55%, #09070e 100%);
    color: #f8fafc;
  }
  section[data-testid="stSidebar"] {
    background-color: #130e1c;
    border-right: 1px solid rgba(212, 175, 55, 0.22);
  }
  .hero-header {
    background: linear-gradient(135deg, rgba(212, 175, 55, 0.14), rgba(157, 23, 77, 0.14));
    border: 1px solid rgba(212, 175, 55, 0.35);
    border-radius: 16px;
    padding: 1.25rem 1.6rem;
    margin-bottom: 1.25rem;
  }
  .hero-title {
    font-size: 1.75rem;
    font-weight: 700;
    background: linear-gradient(90deg, #f3d06b, #d4af37, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
  }
  .match-card {
    background: rgba(24, 18, 36, 0.85);
    border: 1px solid rgba(212, 175, 55, 0.28);
    border-radius: 16px;
    padding: 1.2rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  }
  .score-badge {
    display: inline-block;
    background: linear-gradient(135deg, #d4af37, #b48a1e);
    color: #0d0a14;
    font-weight: 700;
    padding: 0.28rem 0.75rem;
    border-radius: 999px;
    font-size: 0.85rem;
  }
  .tag-pill {
    display: inline-block;
    background: rgba(212, 175, 55, 0.12);
    border: 1px solid rgba(212, 175, 55, 0.3);
    color: #f3d06b;
    padding: 0.2rem 0.6rem;
    border-radius: 8px;
    font-size: 0.78rem;
    margin: 0.25rem 0.35rem 0.25rem 0;
  }
  .ai-reason-box {
    background: rgba(255, 255, 255, 0.04);
    border-left: 3px solid #d4af37;
    padding: 0.75rem 1rem;
    border-radius: 0 10px 10px 0;
    margin-top: 0.75rem;
    font-size: 0.9rem;
    color: #e2e8f0;
  }
</style>
""", unsafe_allow_html=True)

# --- GROQ CLIENT & MODEL FALLBACK CHAIN ---
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    return Groq(api_key=api_key)

# Active high-speed Groq production models with automatic fallback
GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b"
]

def call_groq_with_fallback(prompt, json_mode=False):
    client = get_groq_client()
    if not client:
        raise ValueError("GROQ_API_KEY is missing. Add it to .env locally or Streamlit Secrets in cloud.")

    last_error = None
    for model_name in GROQ_MODELS:
        for attempt in range(2):
            try:
                kwargs = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                completion = client.chat.completions.create(**kwargs)
                return completion.choices[0].message.content
            except Exception as e:
                last_error = e
                err_str = str(e)
                if "429" in err_str or "503" in err_str or "overloaded" in err_str.lower():
                    time.sleep(1.2)
                else:
                    break
    raise last_error

# --- DATA HELPERS ---
DATASET_FILE = "dataset.json"
USERS_FILE = "users.json"

AREA_COORDS = {
    "Hauz Khas, Delhi": [28.5494, 77.2001],
    "Sector 62, Noida": [28.6271, 77.3649],
    "Koramangala, Bangalore": [12.9352, 77.6245],
    "Indiranagar, Bangalore": [12.9784, 77.6408],
    "Cyber City, Gurugram": [28.4950, 77.0895]
}

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- SESSION STATE INITIALIZATION ---
if "user" not in st.session_state:
    st.session_state.user = None
if "profiles" not in st.session_state:
    st.session_state.profiles = load_json(DATASET_FILE, [])
if "matches" not in st.session_state:
    st.session_state.matches = None
if "map_center" not in st.session_state:
    st.session_state.map_center = [28.5494, 77.2001]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 13
if "icebreakers" not in st.session_state:
    st.session_state.icebreakers = {}

# --- TOP HERO BANNER ---
st.markdown("""
<div class="hero-header">
  <h1 class="hero-title">🏠 NestMate AI — Smart Area Flatmate Finder</h1>
  <p style="margin:0.3rem 0 0 0; color:#cbd5e1; font-size:0.95rem;">
    Filter rooms & flatmates by locality and budget, locate pins on OpenStreetMap, and rank compatibility with Groq AI.
  </p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR: ACCOUNT & SEARCH FILTERS ---
with st.sidebar:
    st.subheader("👤 Account")
    if st.session_state.user:
        st.success(f"Logged in as **{st.session_state.user['name']}** (`{st.session_state.user['login_id']}`)")
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        auth_tab1, auth_tab2 = st.tabs(["Login", "Sign Up"])
        with auth_tab1:
            login_id = st.text_input("Login ID", placeholder="umesh", key="l_id")
            login_pw = st.text_input("Password", type="password", placeholder="123", key="l_pw")
            if st.button("Login", use_container_width=True, type="primary"):
                users = load_json(USERS_FILE, [])
                matched_u = next(
                    (u for u in users if u["login_id"] == login_id.strip().lower() and u["password"] == login_pw.strip()),
                    None
                )
                if matched_u:
                    st.session_state.user = matched_u
                    st.rerun()
                else:
                    st.error("Invalid Login ID or Password")
        with auth_tab2:
            new_id = st.text_input("Choose Login ID", key="s_id")
            new_name = st.text_input("Full Name", key="s_name")
            new_pw = st.text_input("Choose Password", type="password", key="s_pw")
            if st.button("Create Account", use_container_width=True):
                if new_id and new_name and new_pw:
                    users = load_json(USERS_FILE, [])
                    if any(u["login_id"] == new_id.strip().lower() for u in users):
                        st.error("Login ID already exists.")
                    else:
                        user_obj = {"login_id": new_id.strip().lower(), "name": new_name.strip(), "password": new_pw.strip()}
                        users.append(user_obj)
                        save_json(USERS_FILE, users)
                        st.session_state.user = user_obj
                        st.rerun()
                else:
                    st.warning("Fill all fields.")

    st.divider()
    st.subheader("🔍 Flatmate Search Filters")

    selected_area = st.selectbox(
        "Preferred Locality",
        ["All Areas", "Hauz Khas, Delhi", "Sector 62, Noida", "Koramangala, Bangalore", "Indiranagar, Bangalore", "Cyber City, Gurugram"],
        index=1
    )

    max_budget = st.slider("Max Monthly Rent (₹)", min_value=5000, max_value=40000, value=16000, step=500)

    col_f, col_g = st.columns(2)
    with col_f:
        food_pref = st.selectbox("Diet", ["Any", "Vegetarian", "Non-Vegetarian", "Eggetarian"])
    with col_g:
        gender_pref = st.selectbox("Gender", ["Any", "Male", "Female"])

    st.caption("Quick Reference Chips:")
    chip_cols = st.columns(2)
    if chip_cols[0].button("🥗 Veg & Quiet", use_container_width=True):
        st.session_state["pref_box"] = "Vegetarian, non-smoker, clean and quiet weekdays"
    if chip_cols[1].button("💻 Night Owl", use_container_width=True):
        st.session_state["pref_box"] = "Night owl coder/student, uses headphones, respects privacy"

    preferences = st.text_area(
        "Your Lifestyle & Ideal Roommate",
        key="pref_box",
        placeholder="Describe sleep schedule, cleanliness, hobbies, metro proximity..."
    )

    run_search = st.button("✨ Rank Matches with Groq AI", type="primary", use_container_width=True)

# --- TABS: FIND MATCHES VS POST ROOM ---
tab_browse, tab_post = st.tabs(["🗺️ Explore Matches & Map", "📸 Post Your Room / Profile"])

with tab_browse:
    # Filter candidates based on sidebar selections
    candidates = []
    for p in st.session_state.profiles:
        if selected_area != "All Areas" and selected_area.lower() not in p["area"].lower():
            continue
        if p["budget"] > max_budget:
            continue
        if food_pref != "Any" and p["food"].lower() != food_pref.lower():
            continue
        if gender_pref != "Any" and p.get("gender", "").lower() != gender_pref.lower():
            continue
        candidates.append(p)

    # Update map focus when area changes
    if selected_area in AREA_COORDS:
        st.session_state.map_center = AREA_COORDS[selected_area]
        st.session_state.map_zoom = 14
    elif selected_area == "All Areas":
        st.session_state.map_center = [22.5, 78.9]
        st.session_state.map_zoom = 5

    # Run Groq AI scoring when button clicked
    if run_search:
        if not candidates:
            st.warning("No flatmates matched your strict filters. Try increasing your budget or selecting 'All Areas'.")
            st.session_state.matches = []
        else:
            with st.spinner("Groq AI is analyzing lifestyle compatibility..."):
                slim_candidates = [{k: v for k, v in c.items() if k != "photo"} for c in candidates]
                prompt = f"""
                You are an expert roommate matchmaking AI.
                User Preferences: "{preferences}"
                User Max Budget: ₹{max_budget}
                Preferred Diet: {food_pref}

                Evaluate these candidates:
                {json.dumps(slim_candidates, indent=2)}

                Return ONLY a valid JSON object with a single key "matches" containing an array sorted from highest to lowest compatibility score:
                {{
                  "matches": [
                    {{
                      "id": <candidate id>,
                      "score": <integer 0-100>,
                      "highlights": ["<shared trait 1>", "<shared trait 2>"],
                      "reason": "<2 concise sentences explaining compatibility and any minor lifestyle difference>"
                    }}
                  ]
                }}
                """
                try:
                    raw_response = call_groq_with_fallback(prompt, json_mode=True)
                    parsed = json.loads(raw_response)
                    ai_list = parsed.get("matches", [])

                    enriched = []
                    for item in ai_list:
                        prof = next((c for c in candidates if c["id"] == item["id"]), None)
                        if prof:
                            enriched.append({**prof, **item})
                    st.session_state.matches = enriched
                except Exception as e:
                    st.error(f"Groq AI Error: {e}")

    # Two-column layout: Left = Match Cards, Right = Interactive OpenStreetMap
    col_cards, col_map = st.columns([1.25, 1])

    display_list = st.session_state.matches if st.session_state.matches is not None else candidates

    with col_cards:
        st.subheader(f"Showing {len(display_list)} Flatmate(s)")
        if not display_list:
            st.info("Adjust your filters in the sidebar to see available rooms and flatmates.")
        for m in display_list:
            with st.container():
                st.markdown('<div class="match-card">', unsafe_allow_html=True)
                c_img, c_info = st.columns([1, 1.6])
                with c_img:
                    st.image(m["photo"], use_container_width=True)
                with c_info:
                    score_html = f'<span class="score-badge">{m["score"]}% AI Match</span>' if "score" in m else ""
                    st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                          <h3 style="margin:0; font-size:1.15rem; color:#f8fafc;">{m['name']}, {m['age']}</h3>
                          {score_html}
                        </div>
                        <p style="margin:0.2rem 0; color:#d4af37; font-weight:700;">₹{m['budget']:,}/mo • {m.get('room_type', 'Shared Flat')}</p>
                        <p style="margin:0.2rem 0; color:#94a3b8; font-size:0.85rem;">{m['occupation']} • 📍 {m['area']}</p>
                    """, unsafe_allow_html=True)

                    tags = [f"🥗 {m['food']}", f"⏰ {m['sleep_schedule']}", f"🚭 Smoking: {m['smoking']}"]
                    for h in m.get("highlights", []):
                        tags.append(f"✨ {h}")
                    st.markdown("".join([f'<span class="tag-pill">{t}</span>' for t in tags]), unsafe_allow_html=True)
                    st.write(m["bio"])

                if "reason" in m:
                    st.markdown(f'<div class="ai-reason-box"><strong>Groq AI Compatibility:</strong> {m["reason"]}</div>', unsafe_allow_html=True)

                b_col1, b_col2 = st.columns(2)
                if b_col1.button(f"📍 Locate {m['name'].split()[0]} on Map", key=f"loc_{m['id']}", use_container_width=True):
                    st.session_state.map_center = [m["lat"], m["lng"]]
                    st.session_state.map_zoom = 16
                    st.rerun()

                if b_col2.button(f"💬 Generate AI Intro", key=f"ice_btn_{m['id']}", use_container_width=True):
                    with st.spinner("Drafting intro message..."):
                        try:
                            ice_prompt = f"""
                            Write a friendly, natural 2-sentence WhatsApp/DM intro message to {m['name']} ({m['occupation']}, lives in {m['area']}, bio: {m['bio']}).
                            My lifestyle: {preferences}.
                            Keep it casual, genuine, and ready to send.
                            """
                            msg = call_groq_with_fallback(ice_prompt, json_mode=False)
                            st.session_state.icebreakers[m["id"]] = msg.strip()
                        except Exception as e:
                            st.error(str(e))

                if m["id"] in st.session_state.icebreakers:
                    st.info(f"**Suggested Message:** {st.session_state.icebreakers[m['id']]}")

                st.markdown('</div>', unsafe_allow_html=True)

    with col_map:
        st.subheader("📍 Live Locality Map")
        f_map = folium.Map(
            location=st.session_state.map_center,
            zoom_start=st.session_state.map_zoom,
            tiles="OpenStreetMap"
        )
        for p in display_list:
            if p.get("lat") and p.get("lng"):
                popup_html = f"""
                <div style="width:170px; font-family:sans-serif;">
                  <b>{p['name']} ({p['age']})</b><br/>
                  <span style="color:#b48a1e; font-weight:bold;">₹{p['budget']}/mo</span><br/>
                  {p['food']} • {p.get('room_type', 'Shared')}<br/>
                  <small>{p['area']}</small>
                </div>
                """
                folium.Marker(
                    [p["lat"], p["lng"]],
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=f"{p['name']} — ₹{p['budget']}/mo",
                    icon=folium.Icon(color="darkred", icon="home", prefix="fa")
                ).add_to(f_map)

        st_folium(f_map, width=None, height=620, returned_objects=[])

with tab_post:
    st.subheader("📸 Post Your Available Room or Flatmate Profile")
    if not st.session_state.user:
        st.warning("Please log in or create an account from the **Sidebar** first to publish a listing.")
    else:
        with st.form("post_room_form", clear_on_submit=True):
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                p_area = st.selectbox("Area / Locality", list(AREA_COORDS.keys()))
                p_budget = st.number_input("Monthly Rent Share (₹)", min_value=3000, max_value=100000, value=15000, step=500)
                p_age = st.number_input("Your Age", min_value=18, max_value=60, value=22)
                p_gender = st.selectbox("Gender", ["Male", "Female"])
            with p_col2:
                p_occupation = st.text_input("Occupation", placeholder="e.g., CS Student / Software Engineer")
                p_room_type = st.text_input("Room Type", value="2BHK Private Room")
                p_food = st.selectbox("Diet", ["Vegetarian", "Non-Vegetarian", "Eggetarian"])
                p_sleep = st.selectbox("Sleep Schedule", ["Night Owl", "Early Bird", "Flexible"])

            p_smoking = st.selectbox("Smoking", ["No", "Occasional", "Yes"])
            uploaded_photo = st.file_uploader("Upload Room / Apartment Photo", type=["jpg", "jpeg", "png", "webp"])
            p_bio = st.text_area("Bio & Roommate Expectations", placeholder="Describe your flat, habits, and ideal flatmate...")

            submitted = st.form_submit_button("Publish Listing to Map & AI", type="primary")
            if submitted:
                base_lat, base_lng = AREA_COORDS[p_area]
                offset = (len(st.session_state.profiles) % 7) * 0.0022

                photo_data = "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80"
                if uploaded_photo is not None:
                    raw_bytes = uploaded_photo.read()
                    b64 = base64.b64encode(raw_bytes).decode("utf-8")
                    photo_data = f"data:{uploaded_photo.type};base64,{b64}"

                new_entry = {
                    "id": max([x["id"] for x in st.session_state.profiles], default=0) + 1,
                    "owner_id": st.session_state.user["login_id"],
                    "name": st.session_state.user["name"],
                    "age": int(p_age),
                    "gender": p_gender,
                    "area": p_area,
                    "lat": base_lat + offset,
                    "lng": base_lng + offset,
                    "budget": int(p_budget),
                    "occupation": p_occupation or "Student / Professional",
                    "sleep_schedule": p_sleep,
                    "food": p_food,
                    "smoking": p_smoking,
                    "room_type": p_room_type,
                    "photo": photo_data,
                    "bio": p_bio
                }
                st.session_state.profiles.append(new_entry)
                save_json(DATASET_FILE, st.session_state.profiles)
                st.session_state.matches = None
                st.success("Your room & profile are live! Switch to the 'Explore Matches & Map' tab to see your pin.")