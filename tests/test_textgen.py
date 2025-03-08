import ollama  # type: ignore
import json
import time


article_text = """
Since the Formula 1 World Drivers' Championship began in 1950 the title has been won by 34 different drivers, 16 of who won more than one championship. Of the multiple champions the most prolific was Juan Manuel Fangio, whose record of five titles stood for five decades until it was eclipsed by the most successful driver in the sport's history. Seven times a champion, Michael Schumacher also holds nearly every scoring record in the book by a considerable margin. Though his ethics were sometimes questioned, as was his decision to make a comeback after retiring, his sheer dominance when in his prime is beyond doubt...

The most extraordinary driver's origins were most ordinary. He was born on 3 January, 1969, near Cologne, Germany, six years before his brother Ralf, who would also become a Formula One driver of note. Their father, a bricklayer, ran the local kart track, at Kerpen, where Mrs Schumacher operated the canteen. As a four-year old Michael enjoyed playing on a pedal kart, though when his father fitted it with a small motorcycle engine the future superstar promptly crashed into a lamppost. But Michael quickly mastered his machine and won his first kart championship at six, following which his far from affluent parents arranged sponsorship from wealthy enthusiasts that enabled Michael to make rapid progress. By 1987 he was German and European kart champion and had left school to work as an apprentice car mechanic, a job that was soon replaced by full-time employment as a race driver. In 1990 he won the German F3 championship and was hired by Mercedes to drive sportscars. The next year he made a stunning Formula One debut, qualifying an astonishing seventh in a Jordan for the Belgian Grand Prix at Spa, whereupon he was immediately snapped up by Benetton, with whom in 1992 he won his first F1 race, again at Spa, among the most demanding circuits of them all.

"""
model_name = "Zephyr"
# model_name = "llama3.2:3B"

start_time = time.time()
prompt = f"""Extract 3 fun and interesting facts from this article.\nMake them engaging, concise, and unique.\nAvoid general infos and focus on surprising or unusual details.\nArticle:\n{article_text}"""
response = ollama.chat(
    model=model_name,
    messages=[
        {
            "role": "user",
            "content": (prompt),
        }
    ],
)
end_time = time.time()
print(f"resp. time: {end_time-start_time}")
print(response["message"]["content"])






prompt = """
Based on the following fun fact:\n
generate a list of YouTube search queries\nsomeone could use to find interesting videos on this topic.\nMake them varied, using different angles like documentaries, expert talks, or analysis.\n\nFun Fact: {fact}\n\nFormat the response as a numbered list.",
"""
