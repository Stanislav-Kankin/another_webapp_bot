@app.post("/open-box")
async def open_box(request: Request):
    authorization = request.headers.get("Authentication")
    try:
        data = safe_parse_webapp_init_data(bot.token, authorization)
    except ValueError:
        return JSONResponse({"success": False, "error": "Unauthorized"}, 401)

    # current_datetime = datetime.utcnow()
    # add_1h = current_datetime + timedelta(hours=3, seconds=30)

    i_cash = randint(0, 1000)
    user = await User.filter(id=data.user.id).first()

    if user.number_of_tries == 0:
    # if user.next_usage and add_1h < tz.make_naive(user.next_usage):  # заменил тут знак
        return JSONResponse(
            {"success": False,
             "error": "Невозможно открыть сейчас. 😢"}
            )

    user.luckyboxes["count"] += 1
    user.luckyboxes["cash"] += i_cash
    user.number_of_tries -= 1
    # user.next_usage = add_1h
    await user.save()

    return JSONResponse({"success": True, "cash": i_cash})