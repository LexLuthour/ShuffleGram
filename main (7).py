
# 🔥 ShuffleGram v2.0 - Enhanced Version  
# Author: OpenAI x Amar Bhai  
# Features: Start, Referral, Upload (15/hour), XP, Shuffle, 👍🏻👎🏻, Comment, Save, Report

import os
import json
import random
import time
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===== ENV SETUP =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 8145864430))  # Amar
DATA_FILE = "data.json"
SETTINGS_FILE = "settings.json"

# ===== FLASK KEEP-ALIVE =====
app = Flask('')

@app.route('/')
def home():
    return "ShuffleGram Running ✅"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===== DATA HANDLING =====
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({"users": {}, "posts": {}, "reports": {}, "referrals": {}, "admins": []}, f)
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "referral_system": False,
            "upload_limit": 15,
            "shuffle_limit": 20,
            "comment_notifications": True
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default_settings, f)
        return default_settings
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# ===== XP SYSTEM =====
def get_level(xp):
    return xp // 50

# ===== ADMIN CHECK =====
def is_admin(user_id):
    data = load_data()
    return str(user_id) == str(ADMIN_ID) or str(user_id) in data.get('admins', [])

# ===== INITIALIZE USER =====
def initialize_user(uid, data):
    if uid not in data['users']:
        data['users'][uid] = {
            "xp": 0,
            "uploads": [],
            "liked": [],
            "disliked": [],
            "saved": [],
            "comments": {},
            "uploaded_at": [],
            "is_verified": False,
            "banned": False,
            "shuffled": [],
            "shuffled_count": 0,
            "referrals": 0,
            "ref_by": None,
            "following": [],
            "followers": [],
            "muted_notifications": [],
            "anonymous_receive": True,
            "anon_conversation": None,
            "anon_messages": [],
            "comment_notifications": True
        }

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = update.effective_user
    data = load_data()
    settings = load_settings()

    # Check if user has joined the required channel
    is_member = await check_channel_membership(context, user.id)
    if not is_member:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/ShuffleGram")],
            [InlineKeyboardButton("✅ I've Joined", callback_data="check_membership")]
        ])
        await update.message.reply_text(
            f"👋 Welcome {user.first_name}!\n\n"
            "🔒 To use ShuffleGram, you must first join our official channel.\n\n"
            "👆 Click 'Join Channel' above, then click 'I've Joined' to continue.",
            reply_markup=keyboard
        )
        return

    initialize_user(uid, data)

    # ✅ Referral system (only if enabled)
    if settings["referral_system"] and context.args:
        ref_id = context.args[0]
        if ref_id != uid and ref_id in data['users'] and not data['users'][uid].get("ref_by"):
            data['users'][uid]['ref_by'] = ref_id
            data['users'][ref_id]['referrals'] += 1

    save_data(data)

    # Different keyboard for admin
    if is_admin(user.id):
        keyboard = [
            [KeyboardButton("🔁 Shuffle"), KeyboardButton("📤 Upload")],
            [KeyboardButton("👤 Profile"), KeyboardButton("📌 Saved")],
            [KeyboardButton("🏆 Leaderboard"), KeyboardButton("💬 Comments Today")],
            [KeyboardButton("🧩 Anonymous Chat"), KeyboardButton("❓ Help")],
            [KeyboardButton("⚙️ Admin Panel")]
        ]
    else:
        keyboard = [
            [KeyboardButton("🔁 Shuffle"), KeyboardButton("📤 Upload")],
            [KeyboardButton("👤 Profile"), KeyboardButton("📌 Saved")],
            [KeyboardButton("🏆 Leaderboard"), KeyboardButton("💬 Comments Today")],
            [KeyboardButton("🧩 Anonymous Chat"), KeyboardButton("❓ Help")]
        ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"👋 Welcome {user.first_name} to ShuffleGram!\n\n"
        "📤 Send a photo to upload\n"
        "🔁 Use /shuffle to explore anonymous pics\n"
        "💬 Comment, 👍🏻 Like, 📌 Save, 🚫 Report\n"
        "👤 Follow users to get notified of their posts\n\n"
        "Enjoy unlimited shuffling! 🎯",
        reply_markup=reply_markup
    )

# ===== ADMIN PANEL =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admin can use this.")
        return

    settings = load_settings()
    
    # Create admin panel keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"Referral System: {'ON' if settings['referral_system'] else 'OFF'}", 
            callback_data="toggle_referral"
        )],
        [InlineKeyboardButton("➖ -1", callback_data="upload_limit_dec"),
         InlineKeyboardButton(f"Upload Limit: {settings['upload_limit']}", callback_data="upload_limit_info"),
         InlineKeyboardButton("➕ +1", callback_data="upload_limit_inc")],
        [InlineKeyboardButton("➖ -1", callback_data="shuffle_limit_dec"),
         InlineKeyboardButton(f"Shuffle Limit: {settings['shuffle_limit']}", callback_data="shuffle_limit_info"),
         InlineKeyboardButton("➕ +1", callback_data="shuffle_limit_inc")],
        [InlineKeyboardButton(
            f"Comment Alerts: {'ON' if settings['comment_notifications'] else 'OFF'}", 
            callback_data="toggle_comments"
        )],
        [InlineKeyboardButton("👑 Manage Admins", callback_data="manage_admins")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_admin")]
    ])

    await update.message.reply_text(
        "⚙️ **Admin Control Panel**\n\n"
        f"🔗 Referral System: {'Enabled' if settings['referral_system'] else 'Disabled'}\n"
        f"📤 Upload Limit: {settings['upload_limit']} per hour\n"
        f"🔁 Shuffle Limit: {settings['shuffle_limit']} before referral\n"
        f"💬 Comment Notifications: {'Enabled' if settings['comment_notifications'] else 'Disabled'}\n\n"
        "Use the buttons below to adjust settings:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

# ===== UPLOAD PHOTO =====
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    settings = load_settings()

    # Check channel membership
    is_member = await check_channel_membership(context, user.id)
    if not is_member:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/ShuffleGram")]
        ])
        await update.message.reply_text(
            "🔒 You must join our channel to upload photos!",
            reply_markup=keyboard
        )
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id
    data = load_data()

    initialize_user(uid, data)

    if data['users'][uid].get("banned"):
        await update.message.reply_text("🚫 You are banned from uploading.")
        return

    # Upload limit check (admin and verified users are unlimited)
    now = time.time()
    uploaded_at = [t for t in data['users'][uid].get("uploaded_at", []) if now - t < 3600]
    upload_limit = settings["upload_limit"]
    
    if (len(uploaded_at) >= upload_limit and 
        not is_admin(user.id) and 
        not data['users'][uid].get("is_verified")):
        await update.message.reply_text(f"⚠️ Only {upload_limit} uploads allowed per hour.")
        return

    post_id = f"{uid}_{int(now)}"
    data['posts'][post_id] = {
        "file_id": file_id,
        "uploader": uid,
        "likes": 0,
        "dislikes": 0,
        "comments": [],
        "timestamp": now,
        "saved_by": [],
        "reported_by": []
    }
    data['users'][uid]['uploads'].append(post_id)
    data['users'][uid]['uploaded_at'] = uploaded_at + [now]
    data['users'][uid]['xp'] += 5
    
    # Notify followers about new post
    followers = data['users'][uid].get('followers', [])
    for follower_id in followers:
        if follower_id not in data['users'][uid].get('muted_notifications', []):
            try:
                uploader_data = data['users'].get(uid, {})
                uploader_level = get_level(uploader_data.get('xp', 0))
                verified_badge = "✅" if uploader_data.get("is_verified") else ""
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("👍🏻 Like", callback_data=f"like|{post_id}"),
                     InlineKeyboardButton("👎🏻 Dislike", callback_data=f"dislike|{post_id}")],
                    [InlineKeyboardButton("💬 Comment", callback_data=f"comment|{post_id}"),
                     InlineKeyboardButton("📌 Save", callback_data=f"save|{post_id}")],
                    [InlineKeyboardButton("🚫 Report", callback_data=f"report|{post_id}"),
                     InlineKeyboardButton("🔕 Mute", callback_data=f"mute|{uid}")]
                ])
                await context.bot.send_photo(
                    follower_id,
                    file_id,
                    caption=f"🔔 User {uid[-4:]} posted a new image!\n👤 Anonymous (Lv{uploader_level}){verified_badge}",
                    reply_markup=keyboard
                )
            except:
                pass  # User might have blocked the bot
    
    save_data(data)
    await update.message.reply_text("✅ Photo uploaded successfully!")

# ===== SHUFFLE =====
async def shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    settings = load_settings()

    # Check channel membership
    is_member = await check_channel_membership(context, update.effective_user.id)
    if not is_member:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/ShuffleGram")]
        ])
        await update.message.reply_text(
            "🔒 You must join our channel to use this feature!",
            reply_markup=keyboard
        )
        return

    data = load_data()
    initialize_user(uid, data)
    user_data = data['users'][uid]

    # Shuffle limit check (only if referral system is enabled and user is not admin/verified)
    if (settings["referral_system"] and 
        len(user_data.get('shuffled', [])) >= settings["shuffle_limit"] and 
        user_data.get("referrals", 0) < 3 and 
        not is_admin(update.effective_user.id) and 
        not user_data.get("is_verified")):
        await update.message.reply_text(
            f"🔒 You have reached the free shuffle limit ({settings['shuffle_limit']}).\n"
            "Refer 3 friends to unlock unlimited shuffle access!\n\n"
            "👉 Share this link:\n"
            f"https://t.me/{context.bot.username}?start={uid}"
        )
        return

    seen = user_data.get("shuffled", [])
    liked = user_data.get("liked", [])
    disliked = user_data.get("disliked", [])
    own_posts = user_data.get("uploads", [])
    all_posts = list(data['posts'].keys())

    # Filter out already seen posts, liked/disliked posts, and own posts
    available = [pid for pid in all_posts if pid not in seen and pid not in liked and pid not in disliked and pid not in own_posts]

    if not available:
        await update.message.reply_text("📭 No new posts available to shuffle. You've seen all available posts!")
        return

    pid = random.choice(available)
    post = data['posts'][pid]
    file_id = post['file_id']
    uploader_uid = post['uploader']
    uploader_data = data['users'].get(uploader_uid, {})
    uploader_level = get_level(uploader_data.get('xp', 0))
    verified_badge = "✅" if uploader_data.get("is_verified") else ""
    caption = f"👍🏻 {post['likes']}    👎🏻 {post['dislikes']}\n\n👤 Anonymous (Lv{uploader_level}){verified_badge}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👍🏻 Like", callback_data=f"like|{pid}"),
         InlineKeyboardButton("👎🏻 Dislike", callback_data=f"dislike|{pid}")],
        [InlineKeyboardButton("💬 Comment", callback_data=f"comment|{pid}"),
         InlineKeyboardButton("📌 Save", callback_data=f"save|{pid}")],
        [InlineKeyboardButton("👤 Follow", callback_data=f"follow|{uploader_uid}"),
         InlineKeyboardButton("🚫 Report", callback_data=f"report|{pid}")],
        [InlineKeyboardButton("🔁 Next", callback_data="next_shuffle")]
    ])

    await update.message.reply_photo(file_id, caption=caption, reply_markup=keyboard)
    user_data['shuffled'].append(pid)
    user_data['shuffled'] = user_data['shuffled'][-1000:]  # Keep last 1000 shuffled posts
    save_data(data)

# ===== BUTTON ACTIONS =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    uid = str(user.id)
    data = load_data()
    settings = load_settings()
    await query.answer()

    # Initialize user if not exists
    initialize_user(uid, data)

    # Admin panel actions
    if is_admin(user.id):
        if query.data == "toggle_referral":
            settings["referral_system"] = not settings["referral_system"]
            save_settings(settings)
            await admin_panel_update(query, settings)
            return
        elif query.data == "upload_limit_inc":
            settings["upload_limit"] += 1
            save_settings(settings)
            await admin_panel_update(query, settings)
            return
        elif query.data == "upload_limit_dec":
            if settings["upload_limit"] > 1:
                settings["upload_limit"] -= 1
                save_settings(settings)
            await admin_panel_update(query, settings)
            return
        elif query.data == "shuffle_limit_inc":
            settings["shuffle_limit"] += 1
            save_settings(settings)
            await admin_panel_update(query, settings)
            return
        elif query.data == "shuffle_limit_dec":
            if settings["shuffle_limit"] > 1:
                settings["shuffle_limit"] -= 1
                save_settings(settings)
            await admin_panel_update(query, settings)
            return
        elif query.data == "toggle_comments":
            settings["comment_notifications"] = not settings["comment_notifications"]
            save_settings(settings)
            await admin_panel_update(query, settings)
            return
        elif query.data == "refresh_admin":
            await admin_panel_update(query, settings)
            return
        elif query.data == "manage_admins":
            await manage_admins_menu(query, context)
            return

    # Handle leaderboard callbacks
    if query.data == "leaderboard_alltime":
        await show_alltime_leaderboard(query, context)
        return
    elif query.data == "leaderboard_daily":
        await show_daily_leaderboard(query, context)
        return

    # Handle make admin callback
    if "|" in query.data and query.data.split("|")[0] == "make_admin":
        if str(query.from_user.id) == str(ADMIN_ID):  # Only main admin can make others admin
            _, target_uid = query.data.split("|")
            if target_uid not in data.get('admins', []):
                if 'admins' not in data:
                    data['admins'] = []
                data['admins'].append(target_uid)
                save_data(data)
                await query.answer(f"✅ User {target_uid} is now an admin!")
                try:
                    await context.bot.send_message(target_uid, "🎉 You have been promoted to admin!")
                except:
                    pass
            else:
                await query.answer("❌ User is already an admin!")
        else:
            await query.answer("❌ Only main admin can promote others!")
        return

    # Handle profile button callbacks
    if "|" in query.data and query.data.split("|")[0] in ["top_posts", "today_posts", "toggle_anon", "toggle_comment_notif"]:
        if query.data.split("|")[0] == "toggle_anon":
            # Toggle anonymous chat setting
            data['users'][uid]['anonymous_receive'] = not data['users'][uid].get('anonymous_receive', True)
            save_data(data)
            
            status = "🔓 ON" if data['users'][uid]['anonymous_receive'] else "🔒 OFF"
            await query.answer(f"Anonymous chat toggled {status}")
            
            # Update the profile message
            await profile_update_after_toggle(query, context)
            return
        elif query.data.split("|")[0] == "toggle_comment_notif":
            # Toggle comment notifications
            data['users'][uid]['comment_notifications'] = not data['users'][uid].get('comment_notifications', True)
            save_data(data)
            
            status = "🔔 ON" if data['users'][uid]['comment_notifications'] else "🔕 OFF"
            await query.answer(f"Comment notifications {status}")
            
            # Update the profile message
            await profile_update_after_toggle(query, context)
            return
        else:
            await handle_profile_buttons(query, context)
            return

    # Handle anonymous reply callbacks
    if "|" in query.data and query.data.split("|")[0] == "anon_reply":
        _, target_uid = query.data.split("|")
        context.user_data['anon_reply_target'] = target_uid
        await query.answer("💭 Send your anonymous reply...")
        await context.bot.send_message(uid, "💭 Type your anonymous reply:")
        return
    
    # Handle anonymous conversation replies
    if "|" in query.data and query.data.split("|")[0] == "anon_reply_conv":
        _, sender_uid = query.data.split("|")
        
        # Check if sender exists and initialize if needed
        initialize_user(sender_uid, data)
        
        # Check if user has anonymous chat enabled
        if not data['users'][uid].get('anonymous_receive', True):
            await query.answer("🔒 You have anonymous chat disabled.")
            return
        
        # Set up conversation mode
        data['users'][uid]['anon_conversation'] = sender_uid
        data['users'][sender_uid]['anon_conversation'] = uid
        save_data(data)
        
        context.user_data['anon_chat_mode'] = True
        await query.answer("💭 Reply mode activated...")
        await context.bot.send_message(uid, "💭 Type your anonymous reply:")
        return

    # Handle comment replies
    if "|" in query.data and query.data.split("|")[0] == "reply_comment":
        _, post_id, comment_idx = query.data.split("|")
        context.user_data['replying_to'] = {'post_id': post_id, 'comment_idx': int(comment_idx)}
        await query.answer("💬 Type your reply...")
        await context.bot.send_message(uid, "💬 Type your reply to the comment:")
        return

    if "|" in query.data:
        action, pid = query.data.split("|")
        post = data['posts'].get(pid)

        if not post:
            await query.edit_message_caption("❌ This post was deleted.")
            return

        if action == "like" and pid not in data['users'][uid]['liked']:
            post['likes'] += 1
            data['users'][uid]['liked'].append(pid)
            data['users'][uid]['xp'] += 1
            # Give uploader +2 XP
            uploader_id = post['uploader']
            if uploader_id in data['users']:
                data['users'][uploader_id]['xp'] += 2

        elif action == "dislike" and pid not in data['users'][uid]['disliked']:
            post['dislikes'] += 1
            data['users'][uid]['disliked'].append(pid)
            # Give uploader +2 XP
            uploader_id = post['uploader']
            if uploader_id in data['users']:
                data['users'][uploader_id]['xp'] += 2

        elif action == "save":
            if pid not in data['users'][uid]['saved']:
                data['users'][uid]['saved'].append(pid)
                await context.bot.send_message(uid, "✅ Saved!")

        elif action == "comment":
            # Show existing comments for this post with reply buttons
            post = data['posts'].get(pid)
            if not post:
                await query.answer("❌ Post not found.")
                return

            comments = post.get('comments', [])
            if not comments:
                await context.bot.send_message(uid, "💬 No comments yet.\nSend your comment to add one:")
                context.user_data['commenting'] = pid
            else:
                await context.bot.send_message(uid, f"💬 Comments ({len(comments)}):")
                
                for i, comment in enumerate(comments[-10:], 1):
                    user_id = comment['user'][-4:]
                    timestamp = comment.get('timestamp', 0)
                    time_str = time.strftime("%H:%M", time.localtime(timestamp)) if timestamp else ""
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔁 Reply", callback_data=f"reply_comment|{pid}|{i-1}")]
                    ])
                    
                    await context.bot.send_message(
                        uid, 
                        f"{i}. User{user_id} {time_str}:\n{comment['text']}", 
                        reply_markup=keyboard
                    )
                
                await context.bot.send_message(uid, "💬 Send your comment to add one:")
                context.user_data['commenting'] = pid

        elif action == "report":
            if uid not in post['reported_by']:
                post['reported_by'].append(uid)
                # If admin reports, delete immediately
                if is_admin(user.id):
                    # Remove post from uploader's uploads list
                    uploader_id = post['uploader']
                    if uploader_id in data['users'] and pid in data['users'][uploader_id]['uploads']:
                        data['users'][uploader_id]['uploads'].remove(pid)
                    del data['posts'][pid]
                    await query.edit_message_caption("⚠️ This post was removed by admin.")
                elif len(post['reported_by']) >= 10:
                    # Remove post from uploader's uploads list
                    uploader_id = post['uploader']
                    if uploader_id in data['users'] and pid in data['users'][uploader_id]['uploads']:
                        data['users'][uploader_id]['uploads'].remove(pid)
                    del data['posts'][pid]
                    await query.edit_message_caption("⚠️ This post was removed (too many reports).")
                else:
                    await context.bot.send_message(uid, "🚨 Reported.")
                    
        elif action == "follow":
            target_uid = pid  # The pid is the target user's ID in this case
            initialize_user(target_uid, data)
            
            if target_uid not in data['users'][uid]['following']:
                data['users'][uid]['following'].append(target_uid)
                data['users'][target_uid]['followers'].append(uid)
                await query.answer("✅ You are now following this user!")
                # Notify the followed user
                try:
                    await context.bot.send_message(target_uid, f"🔔 User {uid[-4:]} started following you!")
                except:
                    pass  # User might have blocked the bot
            else:
                await query.answer("✅ You are already following this user!")
            save_data(data)
            return  # Don't update caption for follow action
        
        elif action == "mute":
            target_uid = pid  # The pid is the target user's ID in this case
            if target_uid not in data['users'][uid].get('muted_notifications', []):
                data['users'][uid]['muted_notifications'].append(target_uid)
                await context.bot.send_message(uid, f"🔕 Muted notifications from User {target_uid[-4:]}!")
            else:
                await context.bot.send_message(uid, f"You have already muted User {target_uid[-4:]}!")
            return

    elif query.data == "check_membership":
        # Check if user joined the channel
        is_member = await check_channel_membership(context, query.from_user.id)
        if is_member:
            await query.edit_message_text("✅ Great! You can now use ShuffleGram!")
            # Create a fake update object for start function
            class FakeMessage:
                def __init__(self, text):
                    self.text = text
                async def reply_text(self, text, reply_markup=None):
                    await context.bot.send_message(query.from_user.id, text, reply_markup=reply_markup)

            class FakeUpdate:
                def __init__(self, user):
                    self.effective_user = user
                    self.message = FakeMessage("/start")

            fake_update = FakeUpdate(query.from_user)
            await start(fake_update, context)
        else:
            await query.answer("❌ Please join the channel first!", show_alert=True)
        return

    elif query.data == "next_shuffle":
       # Handle next shuffle button
        await shuffle_callback(query, context)
        return
    elif query.data == "anon_chat":
        await handle_anon_chat(query, context)
        return

    # Update caption
    if "|" in query.data and "report" not in query.data and "follow" not in query.data and "mute" not in query.data:
        post = data['posts'].get(pid)
        if post:
            uploader_uid = post['uploader']
            uploader_data = data['users'].get(uploader_uid, {})
            uploader_level = get_level(uploader_data.get('xp', 0))
            verified_badge = "✅" if uploader_data.get("is_verified") else ""
            new_caption = f"👍🏻 {post['likes']}    👎🏻 {post['dislikes']}\n\n👤 Anonymous (Lv{uploader_level}){verified_badge}"
            try:
                await query.edit_message_caption(new_caption, reply_markup=query.message.reply_markup)
            except Exception as e:
                # Handle cases where message content hasn't changed
                pass

    save_data(data)

# ===== MANAGE ADMINS MENU =====
async def manage_admins_menu(query, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    admins = data.get('admins', [])
    
    msg = "👑 **Admin Management**\n\n"
    msg += f"🔑 Main Admin: {ADMIN_ID}\n"
    
    if admins:
        msg += "👥 Sub Admins:\n"
        for admin_id in admins:
            msg += f"• {admin_id}\n"
    else:
        msg += "👥 No sub admins yet.\n"
    
    msg += "\nTo make someone admin, use: /makeadmin <user_id>"
    
    await query.edit_message_text(msg, parse_mode='Markdown')

# ===== ADMIN PANEL UPDATE =====
async def admin_panel_update(query, settings):
    # Create admin panel keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"Referral System: {'ON' if settings['referral_system'] else 'OFF'}", 
            callback_data="toggle_referral"
        )],
        [InlineKeyboardButton("➖ -1", callback_data="upload_limit_dec"),
         InlineKeyboardButton(f"Upload Limit: {settings['upload_limit']}", callback_data="upload_limit_info"),
         InlineKeyboardButton("➕ +1", callback_data="upload_limit_inc")],
        [InlineKeyboardButton("➖ -1", callback_data="shuffle_limit_dec"),
         InlineKeyboardButton(f"Shuffle Limit: {settings['shuffle_limit']}", callback_data="shuffle_limit_info"),
         InlineKeyboardButton("➕ +1", callback_data="shuffle_limit_inc")],
        [InlineKeyboardButton(
            f"Comment Alerts: {'ON' if settings['comment_notifications'] else 'OFF'}", 
            callback_data="toggle_comments"
        )],
        [InlineKeyboardButton("👑 Manage Admins", callback_data="manage_admins")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_admin")]
    ])

    try:
        await query.edit_message_text(
            "⚙️ **Admin Control Panel**\n\n"
            f"🔗 Referral System: {'Enabled' if settings['referral_system'] else 'Disabled'}\n"
            f"📤 Upload Limit: {settings['upload_limit']} per hour\n"
            f"🔁 Shuffle Limit: {settings['shuffle_limit']} before referral\n"
            f"💬 Comment Notifications: {'Enabled' if settings['comment_notifications'] else 'Disabled'}\n\n"
            "Use the buttons below to adjust settings:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except:
        pass

# ===== SHUFFLE CALLBACK FOR NEXT BUTTON =====
async def shuffle_callback(query, context: ContextTypes.DEFAULT_TYPE):
    uid = str(query.from_user.id)
    data = load_data()
    settings = load_settings()

    initialize_user(uid, data)
    user_data = data['users'][uid]

    # Shuffle limit check (only if referral system is enabled and user is not admin/verified)
    if (settings["referral_system"] and 
        len(user_data.get('shuffled', [])) >= settings["shuffle_limit"] and 
        user_data.get("referrals", 0) < 3 and 
        not is_admin(query.from_user.id) and 
        not user_data.get("is_verified")):
        await query.edit_message_caption(
            f"🔒 You have reached the free shuffle limit ({settings['shuffle_limit']}).\n"
            "Refer 3 friends to unlock unlimited shuffle access!\n\n"
            "👉 Share this link:\n"
            f"https://t.me/{context.bot.username}?start={uid}"
        )
        return

    seen = user_data.get("shuffled", [])
    liked = user_data.get("liked", [])
    disliked = user_data.get("disliked", [])
    own_posts = user_data.get("uploads", [])
    all_posts = list(data['posts'].keys())

    # Filter out already seen posts, liked/disliked posts, and own posts
    available = [pid for pid in all_posts if pid not in seen and pid not in liked and pid not in disliked and pid not in own_posts]

    if not available:
        await query.edit_message_caption("📭 No new posts available to shuffle. You've seen all available posts!")
        return

    pid = random.choice(available)
    post = data['posts'][pid]
    file_id = post['file_id']
    uploader_uid = post['uploader']
    uploader_data = data['users'].get(uploader_uid, {})
    uploader_level = get_level(uploader_data.get('xp', 0))
    verified_badge = "✅" if uploader_data.get("is_verified") else ""
    caption = f"👍🏻 {post['likes']}    👎🏻 {post['dislikes']}\n\n👤 Anonymous (Lv{uploader_level}){verified_badge}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👍🏻 Like", callback_data=f"like|{pid}"),
         InlineKeyboardButton("👎🏻 Dislike", callback_data=f"dislike|{pid}")],
        [InlineKeyboardButton("💬 Comment", callback_data=f"comment|{pid}"),
         InlineKeyboardButton("📌 Save", callback_data=f"save|{pid}")],
        [InlineKeyboardButton("👤 Follow", callback_data=f"follow|{uploader_uid}"),
         InlineKeyboardButton("🚫 Report", callback_data=f"report|{pid}")],
        [InlineKeyboardButton("🔁 Next", callback_data="next_shuffle")]
    ])

    try:
        # Try to edit the media and caption
        await query.edit_message_media(
            media=query.message.photo[0].file_id,
            reply_markup=keyboard
        )
        await query.edit_message_caption(caption=caption, reply_markup=keyboard)
    except:
        # If editing fails, delete the old message and send a new one
        try:
            await query.message.delete()
        except:
            pass
        
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=file_id,
            caption=caption,
            reply_markup=keyboard
        )

    user_data['shuffled'].append(pid)
    user_data['shuffled'] = user_data['shuffled'][-1000:]  # Keep last 1000 shuffled posts
    save_data(data)

# ===== KEYBOARD BUTTON HANDLER =====
async def keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text

    if text == "🔁 Shuffle":
        await shuffle(update, context)
    elif text == "📤 Upload":
        await update.message.reply_text("📷 Send me a photo to upload!")
    elif text == "👤 Profile":
        await profile(update, context)
    elif text == "📌 Saved":
        await view_saved(update, context)
    elif text == "🏆 Leaderboard":
        await leaderboard(update, context)
    elif text == "💬 Comments Today":
        await comments_today(update, context)
    elif text == "🧩 Anonymous Chat":
        await anonymous_chat_handler(update, context)
    elif text == "❓ Help":
        await help_command(update, context)
    elif text == "⚙️ Admin Panel":
        await admin_panel(update, context)
    else:
        # Handle comments if user is in commenting mode
        await comment_handler(update, context)

# ===== COMMENTS TODAY HANDLER =====
async def comments_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()
    
    initialize_user(uid, data)
    
    now = time.time()
    today_start = now - (now % 86400)
    
    posts_with_comments = {}
    for post_id in data['users'][uid].get('uploads', []):
        if post_id in data['posts']:
            post = data['posts'][post_id]
            today_comments = [c for c in post.get('comments', []) 
                            if c.get('timestamp', 0) >= today_start]
            if today_comments:
                posts_with_comments[post_id] = today_comments
    
    if not posts_with_comments:
        await update.message.reply_text("💬 No comments received today.")
        return
        
    await update.message.reply_text(f"💬 Posts with comments today ({len(posts_with_comments)} posts):")
    
    for post_id, comments in posts_with_comments.items():
        post = data['posts'][post_id]
        uploader_data = data['users'].get(uid, {})
        uploader_level = get_level(uploader_data.get('xp', 0))
        verified_badge = "✅" if uploader_data.get("is_verified") else ""
        
        # Send the post first
        await context.bot.send_photo(
            uid,
            post['file_id'],
            caption=f"💬 Comments today: {len(comments)}\n👤 Anonymous (Lv{uploader_level}){verified_badge}"
        )
        
        # Send each comment with reply button
        for comment in comments:
            user_id = comment['user'][-4:]
            timestamp = time.strftime("%H:%M", time.localtime(comment.get('timestamp', 0)))
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Reply", callback_data=f"anon_reply|{comment['user']}")]
            ])
            
            await context.bot.send_message(
                uid, 
                f"💬 From User{user_id} at {timestamp}:\n\n{comment['text']}", 
                reply_markup=keyboard
            )

# ===== COMMENT MESSAGE =====
async def comment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()
    settings = load_settings()

    initialize_user(uid, data)

    if 'commenting' in context.user_data:
        pid = context.user_data['commenting']
        text = update.message.text
        if pid in data['posts']:
            comment_data = {
                "user": uid, 
                "text": text, 
                "timestamp": time.time(),
                "replies": []
            }
            data['posts'][pid]['comments'].append(comment_data)
            data['users'][uid]['xp'] += 1

            # Notify post uploader
            uploader_id = data['posts'][pid]['uploader']
            if uploader_id != uid and uploader_id in data['users']:  # Don't notify self
                # Check if uploader wants comment notifications
                if data['users'][uploader_id].get('comment_notifications', True):
                    try:
                        await context.bot.send_photo(
                            uploader_id,
                            data['posts'][pid]['file_id'],
                            caption=f"💬 New comment from User {uid[-4:]}:\n\n{text}"
                        )
                    except:
                        pass

            # Notify admin if comment notifications are enabled
            if settings["comment_notifications"]:
                try:
                    await context.bot.send_message(
                        ADMIN_ID, 
                        f"💬 New comment on post {pid}:\n{text}\n\nFrom: User {uid[-4:]}"
                    )
                except:
                    pass

            # Show updated comments count
            comment_count = len(data['posts'][pid]['comments'])
            await update.message.reply_text(f"✅ Comment added! ({comment_count} comments total)")
        else:
            await update.message.reply_text("❌ Post not found.")
        del context.user_data['commenting']
        save_data(data)
    elif 'replying_to' in context.user_data:
        # Handle comment replies
        reply_info = context.user_data['replying_to']
        post_id = reply_info['post_id']
        comment_idx = reply_info['comment_idx']
        text = update.message.text
        
        if post_id in data['posts'] and comment_idx < len(data['posts'][post_id]['comments']):
            # Add reply to the comment
            reply_data = {
                "user": uid,
                "text": text,
                "timestamp": time.time()
            }
            data['posts'][post_id]['comments'][comment_idx]['replies'].append(reply_data)
            
            # Notify the original commenter
            original_commenter = data['posts'][post_id]['comments'][comment_idx]['user']
            if original_commenter != uid and original_commenter in data['users']:
                # Check if commenter wants notifications
                if data['users'][original_commenter].get('comment_notifications', True):
                    try:
                        await context.bot.send_photo(
                            original_commenter,
                            data['posts'][post_id]['file_id'],
                            caption=f"💬 Reply to your comment from User {uid[-4:]}:\n\n{text}"
                        )
                    except:
                        pass
            
            await update.message.reply_text("✅ Reply sent!")
        else:
            await update.message.reply_text("❌ Comment not found.")
        del context.user_data['replying_to']
        save_data(data)
    elif 'anon_chat_mode' in context.user_data:
        # Handle anonymous chat messages
        await handle_anonymous_message(update, context)
        save_data(data)
    elif 'anon_reply_target' in context.user_data:
        # Handle anonymous replies
        await handle_anonymous_reply(update, context)
        save_data(data)

# ===== /PROFILE COMMAND =====
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    data = load_data()
    
    initialize_user(uid, data)
    udata = data['users'][uid]

    uploads = len(udata['uploads'])
    xp = udata['xp']
    lvl = get_level(xp)
    refs = udata.get('referrals', 0)
    saved = len(udata.get("saved", []))
    verified = "✅" if udata.get("is_verified") else "❌"
    following = len(udata.get("following", []))
    followers = len(udata.get("followers", []))

    # Count today's posts
    import time
    now = time.time()
    today_start = now - (now % 86400) # Start of today in seconds
    today_posts = sum(1 for t in udata.get('uploaded_at', []) if t >= today_start)

    # Anonymous chat status
    anon_status = "🔓 ON" if udata.get('anonymous_receive', True) else "🔒 OFF"
    comment_notif_status = "🔔 ON" if udata.get('comment_notifications', True) else "🔕 OFF"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Today's Posts", callback_data=f"today_posts|{uid}"),
         InlineKeyboardButton("🏆 Top 10 Posts", callback_data=f"top_posts|{uid}")],
        [InlineKeyboardButton(f"Anonymous Chat: {anon_status}", callback_data=f"toggle_anon|{uid}"),
         InlineKeyboardButton(f"Comment Alerts: {comment_notif_status}", callback_data=f"toggle_comment_notif|{uid}")]
    ])

    await update.message.reply_text(
        f"👤 Your Profile:\n"
        f"⭐ Level: {lvl} ({xp} XP)\n"
        f"📤 Uploads: {uploads}\n"
        f"📌 Saved: {saved}\n"
        f"📨 Referrals: {refs}\n"
        f"✔️ Verified: {verified}\n"
        f"👣 Following: {following}\n"
        f"👥 Followers: {followers}\n"
        f"📅 Today's Posts: {today_posts}",
        reply_markup=keyboard
    )

# ===== /SHARE COMMAND =====
async def share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    settings = load_settings()
    
    if settings["referral_system"]:
        await update.message.reply_text(
            "🎉 Share this bot with your friends and unlock unlimited shuffles!\n\n"
            f"👉 Your referral link:\nhttps://t.me/{context.bot.username}?start={uid}"
        )
    else:
        await update.message.reply_text(
            "🎉 Share this bot with your friends!\n\n"
            f"👉 Bot link:\nhttps://t.me/{context.bot.username}"
        )

# ===== /LEADERBOARD COMMAND =====
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        # Admin gets choice between all-time and daily leaderboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 All Time Top 10", callback_data="leaderboard_alltime")],
            [InlineKeyboardButton("📅 Today's Top 10", callback_data="leaderboard_daily")]
        ])
        await update.message.reply_text(
            "🏆 **Leaderboard Options**\n\nChoose which leaderboard to view:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        # Regular users see all-time leaderboard
        await show_alltime_leaderboard_message(update, context)

async def show_alltime_leaderboard_message(update, context):
    data = load_data()
    leaderboard_data = []

    for uid, udata in data['users'].items():
        leaderboard_data.append((uid, udata['xp']))

    leaderboard_data.sort(key=lambda x: x[1], reverse=True)
    top10 = leaderboard_data[:10]

    msg = "🏆 All Time Top 10 Users:\n\n"
    for i, (uid, xp) in enumerate(top10, 1):
        lvl = get_level(xp)
        if is_admin(update.effective_user.id):
            # Admin sees actual user names/usernames
            try:
                user_info = await context.bot.get_chat(uid)
                name = user_info.first_name or f"User {uid[-4:]}"
                if user_info.username:
                    name += f" (@{user_info.username})"
            except:
                name = f"User {uid[-4:]}"
        else:
            name = f"User {uid[-4:]}"  # Regular users see masked IDs
        msg += f"{i}. {name} — {xp} XP (Lv{lvl})\n"

    await update.message.reply_text(msg)

async def show_alltime_leaderboard(query, context):
    data = load_data()
    leaderboard_data = []

    for uid, udata in data['users'].items():
        leaderboard_data.append((uid, udata['xp']))

    leaderboard_data.sort(key=lambda x: x[1], reverse=True)
    top10 = leaderboard_data[:10]

    msg = "🏆 All Time Top 10 Users:\n\n"
    for i, (uid, xp) in enumerate(top10, 1):
        lvl = get_level(xp)
        try:
            user_info = await context.bot.get_chat(uid)
            name = user_info.first_name or f"User {uid[-4:]}"
            if user_info.username:
                name += f" (@{user_info.username})"
        except:
            name = f"User {uid[-4:]}"
        msg += f"{i}. {name} — {xp} XP (Lv{lvl})\n"

    await query.edit_message_text(msg)

async def show_daily_leaderboard(query, context):
    data = load_data()
    now = time.time()
    today_start = now - (now % 86400)
    
    # Calculate XP gained today for each user
    daily_xp = []
    for uid, udata in data['users'].items():
        # Calculate uploads today
        today_uploads = sum(1 for t in udata.get('uploaded_at', []) if t >= today_start)
        upload_xp = today_uploads * 5  # 5 XP per upload
        
        # Calculate likes given today (approximate)
        like_xp = 0
        for post_id, post in data['posts'].items():
            if post['timestamp'] >= today_start:
                if uid in udata.get('liked', []):
                    like_xp += 1  # 1 XP per like
        
        # Calculate comments made today (approximate)
        comment_xp = 0
        for post_id, post in data['posts'].items():
            for comment in post.get('comments', []):
                if comment['user'] == uid and comment.get('timestamp', 0) >= today_start:
                    comment_xp += 1  # 1 XP per comment
        
        # Calculate XP from likes/dislikes received today
        received_xp = 0
        for post_id in udata.get('uploads', []):
            if post_id in data['posts']:
                post = data['posts'][post_id]
                if post['timestamp'] >= today_start:
                    received_xp += (post['likes'] + post['dislikes']) * 2  # 2 XP per like/dislike received
        
        total_daily_xp = upload_xp + like_xp + comment_xp + received_xp
        
        if total_daily_xp > 0:
            daily_xp.append((uid, total_daily_xp))
    
    daily_xp.sort(key=lambda x: x[1], reverse=True)
    top10_daily = daily_xp[:10]
    
    if not top10_daily:
        await query.edit_message_text("📅 No activity today yet!")
        return
    
    msg = "📅 Today's Top 10 Users (XP gained today):\n\n"
    for i, (uid, daily_xp_gained) in enumerate(top10_daily, 1):
        try:
            user_info = await context.bot.get_chat(uid)
            name = user_info.first_name or f"User {uid[-4:]}"
            if user_info.username:
                name += f" (@{user_info.username})"
        except:
            name = f"User {uid[-4:]}"
        msg += f"{i}. {name} — +{daily_xp_gained} XP today\n"
    
    await query.edit_message_text(msg)

# ===== /DELETE COMMAND =====
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()

    initialize_user(uid, data)

    posts = data['users'][uid]['uploads']

    if not posts:
        await update.message.reply_text("❌ You have no uploads.")
        return

    buttons = [
        [InlineKeyboardButton(f"🗑️ Delete Post {i+1}", callback_data=f"del|{pid}")]
        for i, pid in enumerate(posts[-10:])
    ]
    await update.message.reply_text("Select a post to delete:", reply_markup=InlineKeyboardMarkup(buttons))

async def delete_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = str(query.from_user.id)
    data = load_data()
    await query.answer()

    if "|" in query.data:
        _, pid = query.data.split("|")
        if pid in data['posts'] and data['posts'][pid]['uploader'] == uid:
            del data['posts'][pid]
            data['users'][uid]['uploads'].remove(pid)
            await query.edit_message_text("✅ Post deleted.")
            save_data(data)
        else:
            await query.edit_message_text("❌ Cannot delete this post.")

# ===== MAKE ADMIN COMMAND =====
async def make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ Only main admin can use this.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /makeadmin <user_id>")
        return
    
    target_uid = context.args[0]
    data = load_data()
    
    if 'admins' not in data:
        data['admins'] = []
    
    if target_uid not in data['admins']:
        data['admins'].append(target_uid)
        save_data(data)
        await update.message.reply_text(f"✅ User {target_uid} is now an admin!")
        try:
            await context.bot.send_message(target_uid, "🎉 You have been promoted to admin!")
        except:
            pass
    else:
        await update.message.reply_text("❌ User is already an admin!")

# ===== /BAN & /UNBAN =====
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admin can use this.")
        return

    data = load_data()

    # Check if replying to a message (ban by reply)
    if update.message.reply_to_message:
        # Extract post ID from the replied message caption or use message info
        replied_msg = update.message.reply_to_message
        if replied_msg.photo and replied_msg.caption:
            # Find the post by searching through all posts
            target_uid = None
            for pid, post_data in data['posts'].items():
                if post_data['file_id'] == replied_msg.photo[-1].file_id:
                    target_uid = post_data['uploader']
                    break

            if target_uid:
                initialize_user(target_uid, data)
                data['users'][target_uid]['banned'] = True
                # Remove all posts by this user
                posts_to_remove = [pid for pid, post in data['posts'].items() if post['uploader'] == target_uid]
                for pid in posts_to_remove:
                    del data['posts'][pid]
                data['users'][target_uid]['uploads'] = []
                save_data(data)
                await update.message.reply_text(f"🚫 User {target_uid} banned and all their posts removed.")
            else:
                await update.message.reply_text("❌ Could not identify the post uploader.")
        else:
            await update.message.reply_text("❌ Please reply to a photo post to ban the uploader.")
        return

    # Original ban by user ID
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id> or reply to a post to ban the uploader")
        return
    uid = context.args[0]
    initialize_user(uid, data)
    data['users'][uid]['banned'] = True
    # Remove all posts by this user
    posts_to_remove = [pid for pid, post in data['posts'].items() if post['uploader'] == uid]
    for pid in posts_to_remove:
        del data['posts'][pid]
    data['users'][uid]['uploads'] = []
    save_data(data)
    await update.message.reply_text(f"🚫 User {uid} banned and all their posts removed.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admin can use this.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    uid = context.args[0]
    data = load_data()
    initialize_user(uid, data)
    data['users'][uid]['banned'] = False
    save_data(data)
    await update.message.reply_text(f"✅ User {uid} unbanned.")

# ===== /VERIFY =====
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admin can use this.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /verify <user_id>")
        return
    uid = context.args[0]
    data = load_data()
    initialize_user(uid, data)
    data['users'][uid]['is_verified'] = True

    # Send notification to the user
    try:
        await context.bot.send_message(uid, "✅ Congratulations! You are now verified and can upload unlimited images and do unlimited shuffles!")
    except Exception as e:
        print(f"Failed to send verification message to user {uid}: {e}")

    save_data(data)
    await update.message.reply_text(f"✅ User {uid} verified.")

# ===== /TRENDING =====
async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    sorted_posts = sorted(data['posts'].items(), key=lambda x: x[1]['likes'], reverse=True)[:5]

    if not sorted_posts:
        await update.message.reply_text("📭 No trending posts.")
        return

    for pid, post in sorted_posts:
        uploader_data = data['users'].get(post['uploader'], {})
        uploader_level = get_level(uploader_data.get('xp', 0))
        verified_badge = "✅" if uploader_data.get("is_verified") else ""
        await update.message.reply_photo(
            post['file_id'], 
            caption=f"🔥 Trending — 👍🏻 {post['likes']} | 👤 Anonymous (Lv{uploader_level}){verified_badge}"
        )

# ===== /SAVED POSTS =====
async def view_saved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()

    initialize_user(uid, data)

    saved = data['users'][uid].get('saved', [])

    if not saved:
        await update.message.reply_text("📭 No saved posts.")
        return

    await update.message.reply_text(f"📌 Your Saved Posts ({len(saved)} total):")
    
    # Send all saved posts
    for pid in saved:
        if pid in data['posts']:
            post = data['posts'][pid]
            uploader_data = data['users'].get(post['uploader'], {})
            uploader_level = get_level(uploader_data.get('xp', 0))
            verified_badge = "✅" if uploader_data.get("is_verified") else ""
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👍🏻 Like", callback_data=f"like|{pid}"),
                 InlineKeyboardButton("👎🏻 Dislike", callback_data=f"dislike|{pid}")],
                [InlineKeyboardButton("💬 Comment", callback_data=f"comment|{pid}"),
                 InlineKeyboardButton("🚫 Report", callback_data=f"report|{pid}")]
            ])
            
            await context.bot.send_photo(
                uid,
                post['file_id'], 
                caption=f"📌 Saved Post\n👍🏻 {post['likes']} | 👎🏻 {post['dislikes']}\n👤 Anonymous (Lv{uploader_level}){verified_badge}",
                reply_markup=keyboard
            )

# ===== /COMMENTS =====
async def view_comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /comments <post_id>")
        return
    pid = context.args[0]
    data = load_data()
    post = data['posts'].get(pid)
    if not post:
        await update.message.reply_text("❌ Post not found.")
        return
    comments = post.get('comments', [])
    if not comments:
        await update.message.reply_text("💬 No comments.")
    else:
        msg = "💬 Comments:\n\n"
        for c in comments[-10:]:
            msg += f"- {c['text']}\n"
        await update.message.reply_text(msg)

# ===== /REPORTS =====
async def view_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only.")
        return

    data = load_data()
    reported = [(pid, len(post['reported_by'])) for pid, post in data['posts'].items() if post['reported_by']]
    reported.sort(key=lambda x: x[1], reverse=True)

    if not reported:
        await update.message.reply_text("✅ No reported posts.")
        return

    await update.message.reply_text(f"🚨 Found {len(reported)} reported posts. Sending them now...")
    
    for pid, count in reported[:10]:
        post = data['posts'][pid]
        uploader_data = data['users'].get(post['uploader'], {})
        uploader_level = get_level(uploader_data.get('xp', 0))
        verified_badge = "✅" if uploader_data.get("is_verified") else ""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Post", callback_data=f"admin_delete|{pid}"),
             InlineKeyboardButton("❌ Ignore Report", callback_data=f"ignore_report|{pid}")],
            [InlineKeyboardButton("🚫 Ban Uploader", callback_data=f"ban_uploader|{post['uploader']}")]
        ])
        
        await context.bot.send_photo(
            update.effective_user.id,
            post['file_id'],
            caption=f"🚨 Reported Post ({count} reports)\n"
                    f"📝 Post ID: {pid}\n"
                    f"👤 Uploader: User {post['uploader'][-4:]}\n"
                    f"👍🏻 {post['likes']} | 👎🏻 {post['dislikes']}\n"
                    f"👤 Anonymous (Lv{uploader_level}){verified_badge}",
            reply_markup=keyboard
        )

# ===== ADMIN STATS =====
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Only admin can use this.")
        return

    data = load_data()
    settings = load_settings()
    total_users = len(data['users'])
    total_posts = len(data['posts'])
    total_uploads = sum(len(user.get('uploads', [])) for user in data['users'].values())
    verified_users = sum(1 for user in data['users'].values() if user.get('is_verified', False))
    banned_users = sum(1 for user in data['users'].values() if user.get('banned', False))

    # Recent activity (last 24 hours)
    now = time.time()
    recent_uploads = sum(
        len([t for t in user.get('uploaded_at', []) if now - t < 86400])
        for user in data['users'].values()
    )

    # Active users (last 24 hours)
    active_users = sum(
        1 for user in data['users'].values()
        if any(now - t < 86400 for t in user.get('uploaded_at', []))
    )

    # Most reported posts
    reported_posts = [(pid, len(post['reported_by'])) for pid, post in data['posts'].items() if post['reported_by']]
    reported_posts.sort(key=lambda x: x[1], reverse=True)

    await update.message.reply_text(
        f"📊 **Admin Dashboard**\n\n"
        f"👥 Total Users: {total_users}\n"
        f"📤 Total Posts: {total_posts}\n"
        f"📸 Total Uploads: {total_uploads}\n"
        f"✅ Verified Users: {verified_users}\n"
        f"🚫 Banned Users: {banned_users}\n"
        f"📈 Recent Uploads (24h): {recent_uploads}\n"
        f"🟢 Active Users (24h): {active_users}\n"
        f"🚨 Reported Posts: {len(reported_posts)}\n\n"
        f"**Current Settings:**\n"
        f"🔗 Referral System: {'ON' if settings['referral_system'] else 'OFF'}\n"
        f"📤 Upload Limit: {settings['upload_limit']}/hour\n"
        f"🔁 Shuffle Limit: {settings['shuffle_limit']}\n"
        f"💬 Comment Alerts: {'ON' if settings['comment_notifications'] else 'OFF'}\n\n"
        f"**Admin Powers:**\n"
        f"• Unlimited uploads & shuffles\n"
        f"• Auto-delete posts when reporting\n"
        f"• Reply to posts with /ban to ban uploader\n"
        f"• Use /adminpanel to change settings",
        parse_mode='Markdown'
    )

# ===== PROFILE BUTTON HANDLERS =====
async def handle_profile_buttons(query, context: ContextTypes.DEFAULT_TYPE):
    uid = str(query.from_user.id)
    data = load_data()
    action, target_uid = query.data.split("|")
    
    if uid != target_uid:
        await query.answer("❌ You can only view your own profile data.")
        return

    user_data = data['users'].get(uid, {})
    
    if action == "top_posts":
        # Get user's own posts and sort by likes
        user_posts = []
        for post_id in user_data.get('uploads', []):
            if post_id in data['posts']:
                post = data['posts'][post_id]
                user_posts.append((post_id, post['likes'], post))
        
        # Sort by likes (descending) and get top 10
        user_posts.sort(key=lambda x: x[1], reverse=True)
        top_posts = user_posts[:10]
        
        if not top_posts:
            await query.answer("📭 No posts found.")
            return
            
        await query.answer("🏆 Showing your top 10 posts...")
        for i, (post_id, likes, post) in enumerate(top_posts, 1):
            uploader_level = get_level(user_data.get('xp', 0))
            verified_badge = "✅" if user_data.get("is_verified") else ""
            
            await context.bot.send_photo(
                uid,
                post['file_id'],
                caption=f"🏆 #{i} Your Top Post\n👍🏻 {likes} likes | 👎🏻 {post['dislikes']}\n👤 Anonymous (Lv{uploader_level}){verified_badge}"
            )
    
    elif action == "today_posts":
        now = time.time()
        today_start = now - (now % 86400)
        
        today_uploads = []
        for post_id in user_data.get('uploads', []):
            if post_id in data['posts']:
                post = data['posts'][post_id]
                if post['timestamp'] >= today_start:
                    today_uploads.append((post_id, post['timestamp']))
        
        if not today_uploads:
            await query.answer("📅 No posts today.")
            return
            
        await query.answer("📅 Showing today's posts...")
        for post_id, upload_time in today_uploads:
            post = data['posts'][post_id]
            time_str = time.strftime("%H:%M", time.localtime(upload_time))
            uploader_level = get_level(user_data.get('xp', 0))
            verified_badge = "✅" if user_data.get("is_verified") else ""
            await context.bot.send_photo(
                uid,
                post['file_id'],
                caption=f"📅 Posted today at {time_str}\n👍🏻 {post['likes']} | 👎🏻 {post['dislikes']} | 💬 {len(post.get('comments', []))}\n👤 Anonymous (Lv{uploader_level}){verified_badge}"
            )

# ===== ANONYMOUS MESSAGE HANDLERS =====
async def handle_anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()
    message_text = update.message.text
    
    # Find eligible users for anonymous chat
    eligible_users = []
    for user_id, user_data in data['users'].items():
        if (user_id != uid and 
            user_data.get('anonymous_receive', True) and 
            not user_data.get('anon_conversation')):  # Not in conversation
            eligible_users.append(user_id)
    
    if not eligible_users:
        await update.message.reply_text(
            "😔 No users available for anonymous chat right now. Try again later!"
        )
        del context.user_data['anon_chat_mode']
        return
    
    import random
    target_user = random.choice(eligible_users)
    
    # Set up conversation
    data['users'][uid]['anon_conversation'] = target_user
    data['users'][target_user]['anon_conversation'] = uid
    
    # Store message for cleanup (delete after 1 day)
    import time
    message_data = {
        'from': uid,
        'to': target_user,
        'message': message_text,
        'timestamp': time.time()
    }
    
    # Initialize anon_messages if not exists
    if 'anon_messages' not in data:
        data['anon_messages'] = []
    
    data['anon_messages'].append(message_data)
    
    # Clean old messages (older than 1 day)
    now = time.time()
    one_day_ago = now - 86400
    data['anon_messages'] = [msg for msg in data['anon_messages'] if msg['timestamp'] > one_day_ago]
    
    # Send to target user
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Reply", callback_data=f"anon_reply_conv|{uid}")]
        ])
        
        await context.bot.send_message(
            target_user,
            f"💭 **Anonymous Message**\n\n{message_text}\n\n_Someone wants to chat anonymously!_",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            "✅ Anonymous message sent! If they reply, you'll get notified.\n\n"
            "💭 Send another message to continue the conversation, or type /stop to end it."
        )
        
    except Exception as e:
        # If sending fails, clean up conversation
        data['users'][uid]['anon_conversation'] = None
        data['users'][target_user]['anon_conversation'] = None
        await update.message.reply_text("❌ Failed to send message. Try again later.")
    
    del context.user_data['anon_chat_mode']

async def handle_anonymous_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()
    message_text = update.message.text
    target_user = context.user_data['anon_reply_target']
    
    # Check if target user exists and initialize if needed
    initialize_user(target_user, data)
    
    # Check if target user has anonymous chat enabled
    if not data['users'].get(target_user, {}).get('anonymous_receive', True):
        await update.message.reply_text("❌ That user has disabled anonymous messages.")
        del context.user_data['anon_reply_target']
        return
    
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Reply", callback_data=f"anon_reply|{uid}")]
        ])
        
        await context.bot.send_message(
            target_user,
            f"💭 **Anonymous Reply**\n\n{message_text}\n\n_Anonymous reply to your comment_",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        await update.message.reply_text("✅ Anonymous reply sent!")
        
    except:
        await update.message.reply_text("❌ Failed to send reply. User may have blocked the bot.")
    
    del context.user_data['anon_reply_target']

# ===== ANONYMOUS CHAT HANDLERS =====
async def handle_anon_chat(query, context: ContextTypes.DEFAULT_TYPE):
    uid = str(query.from_user.id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💭 Send Anonymous Message", callback_data="send_anon_msg")],
        [InlineKeyboardButton("📨 Check Messages", callback_data="check_anon_msg")],
        [InlineKeyboardButton("🔙 Back to Profile", callback_data="back_profile")]
    ])
    
    await query.edit_message_text(
        "💭 **Anonymous Chat**\n\n"
        "Send anonymous messages to random users or check your received messages.\n"
        "All messages are completely anonymous!\n\n"
        "Choose an option:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def handle_anon_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()
    message_text = update.message.text
    
    # Initialize anonymous messages if not exists
    if 'anon_messages' not in data:
        data['anon_messages'] = {}
    
    # Find a random user to send message to (exclude self)
    all_users = [u for u in data['users'].keys() if u != uid]
    if not all_users:
        await update.message.reply_text("❌ No other users to send message to.")
        del context.user_data['anon_chat']
        return
    
    import random
    target_user = random.choice(all_users)

    # Store the message
    if target_user not in data['anon_messages']:
        data['anon_messages'][target_user] = []
    
    data['anon_messages'][target_user].append({
        'message': message_text,
        'timestamp': time.time()
    })
    
    # Send confirmation to sender
    await update.message.reply_text("✅ Anonymous message sent to a random user!")
    
    # Notify recipient
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💭 Reply Anonymously", callback_data="reply_anon")],
            [InlineKeyboardButton("📨 Check All Messages", callback_data="check_anon_msg")]
        ])
        
        await context.bot.send_message(
            target_user,
            f"💭 **Anonymous Message**\n\n{message_text}\n\n_Someone sent you this anonymously!_",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except:
        pass  # User might have blocked the bot
    
    del context.user_data['anon_chat']

# ===== ANONYMOUS CHAT HANDLER =====
async def anonymous_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()
    
    initialize_user(uid, data)
    
    # Check if user has anonymous chat enabled
    if not data['users'][uid].get('anonymous_receive', True):
        await update.message.reply_text(
            "🔒 Anonymous chat is disabled for you. Enable it in your profile settings to use this feature."
        )
        return
    
    await update.message.reply_text(
        "🧩 **Anonymous Chat Mode**\n\n"
        "You've entered anonymous chat mode. Say something and we'll send it to another random user.\n\n"
        "💭 Type your message:",
        parse_mode='Markdown'
    )
    context.user_data['anon_chat_mode'] = True

async def profile_update_after_toggle(query, context: ContextTypes.DEFAULT_TYPE):
    """Update profile message after toggling settings"""
    user = query.from_user
    uid = str(user.id)
    data = load_data()
    udata = data['users'].get(uid, {})

    uploads = len(udata.get('uploads', []))
    xp = udata.get('xp', 0)
    lvl = get_level(xp)
    refs = udata.get('referrals', 0)
    saved = len(udata.get("saved", []))
    verified = "✅" if udata.get("is_verified") else "❌"
    following = len(udata.get("following", []))
    followers = len(udata.get("followers", []))

    import time
    now = time.time()
    today_start = now - (now % 86400)
    today_posts = sum(1 for t in udata.get('uploaded_at', []) if t >= today_start)

    anon_status = "🔓 ON" if udata.get('anonymous_receive', True) else "🔒 OFF"
    comment_notif_status = "🔔 ON" if udata.get('comment_notifications', True) else "🔕 OFF"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Today's Posts", callback_data=f"today_posts|{uid}"),
         InlineKeyboardButton("🏆 Top 10 Posts", callback_data=f"top_posts|{uid}")],
        [InlineKeyboardButton(f"Anonymous Chat: {anon_status}", callback_data=f"toggle_anon|{uid}"),
         InlineKeyboardButton(f"Comment Alerts: {comment_notif_status}", callback_data=f"toggle_comment_notif|{uid}")]
    ])

    try:
        await query.edit_message_text(
            f"👤 Your Profile:\n"
            f"⭐ Level: {lvl} ({xp} XP)\n"
            f"📤 Uploads: {uploads}\n"
            f"📌 Saved: {saved}\n"
            f"📨 Referrals: {refs}\n"
            f"✔️ Verified: {verified}\n"
            f"👣 Following: {following}\n"
            f"👥 Followers: {followers}\n"
            f"📅 Today's Posts: {today_posts}",
            reply_markup=keyboard
        )
    except:
        pass

# ===== CHECK CHANNEL MEMBERSHIP =====
async def check_anonymous_messages(query, context: ContextTypes.DEFAULT_TYPE):
    uid = str(query.from_user.id)
    data = load_data()
    
    if 'anon_messages' not in data:
        data['anon_messages'] = {}
    
    user_messages = data['anon_messages'].get(uid, [])
    
    if not user_messages:
        await query.answer("📭 No anonymous messages.")
        return
    
    await query.answer("📨 Showing your anonymous messages...")
    
    # Show last 10 messages
    recent_messages = user_messages[-10:]
    
    for i, msg in enumerate(recent_messages, 1):
        timestamp = time.strftime("%d/%m %H:%M", time.localtime(msg['timestamp']))
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💭 Reply Anonymously", callback_data="reply_anon")]
        ])
        
        await context.bot.send_message(
            uid,
            f"💭 **Anonymous Message #{i}**\n"
            f"📅 {timestamp}\n\n"
            f"{msg['message']}\n\n"
            f"_From: Anonymous User_",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        member = await context.bot.get_chat_member(chat_id="@ShuffleGram", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# ===== /STOP COMMAND =====
async def stop_anonymous_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = load_data()
    
    initialize_user(uid, data)
    
    conversation_partner = data['users'][uid].get('anon_conversation')
    
    if conversation_partner:
        # End conversation for both users
        data['users'][uid]['anon_conversation'] = None
        if conversation_partner in data['users']:
            data['users'][conversation_partner]['anon_conversation'] = None
            try:
                await context.bot.send_message(
                    conversation_partner,
                    "💭 Anonymous conversation ended by the other user."
                )
            except:
                pass
        save_data(data)
        await update.message.reply_text("✅ Anonymous conversation ended.")
    else:
        await update.message.reply_text("❌ You are not in an anonymous conversation.")
    
    # Clear any chat modes
    if 'anon_chat_mode' in context.user_data:
        del context.user_data['anon_chat_mode']

# ===== /HELP COMMAND =====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **ShuffleGram Bot Help**

📋 **Available Commands:**

🚀 **Main Features:**
/start - Start using the bot
/shuffle - Explore random posts
/profile - View your profile & stats
/help - Show this help message

📤 **Content Management:**
• Send a photo to upload
/delete - Delete your uploaded posts
/saved - View your saved posts
/trending - See trending posts

📊 **Social Features:**
/leaderboard - View top users by XP
/comments <post_id> - View comments on a post

🔧 **Admin Commands:**
/adminpanel - Admin control panel (Admin only)
/ban <user_id> - Ban a user (Admin only)
/unban <user_id> - Unban a user (Admin only)
/verify <user_id> - Verify a user (Admin only)
/makeadmin <user_id> - Make someone admin (Main admin only)
/reports - View reported posts (Admin only)
/stats - View detailed bot statistics (Admin only)

🛡️ **Admin Powers:**
• Unlimited uploads and shuffles
• Auto-delete posts when reporting
• Reply to any post with /ban to ban the uploader
• All posts and user data removed when banning

💡 **How to Use:**
1. Send photos to upload and earn 5 XP
2. Use /shuffle to discover posts
3. Like 👍🏻, comment 💬, save 📌, or report 🚫 posts
4. Earn XP to climb the leaderboard!

🎯 **XP System:**
• Upload photo: +5 XP
• Like a post: +1 XP
• Comment on post: +1 XP
• Receive like/dislike: +2 XP
• Level up every 50 XP

Enjoy ShuffleGram! 🎉
"""
    await update.message.reply_text(help_text)

# ===== MAIN FUNCTION =====
def main():
    keep_alive()

    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("shuffle", shuffle))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("makeadmin", make_admin))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("saved", view_saved))
    application.add_handler(CommandHandler("comments", view_comments))
    application.add_handler(CommandHandler("reports", view_reports))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("adminpanel", admin_panel))
    application.add_handler(CommandHandler("share", share))
    application.add_handler(CommandHandler("stop", stop_anonymous_chat))

    # Message + Callback handlers
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyboard_handler))
    application.add_handler(CallbackQueryHandler(delete_button_handler, pattern="^del\\|"))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🔥 ShuffleGram Bot Started!")
    application.run_polling()

if __name__ == '__main__':
    main()
if __name__ == "__main__":
    keep_alive()
    application.run_polling()