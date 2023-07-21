help_menu_message = """Available Commands
1. /start
    ⇒ Tell ATL BItLab bot to begin listening to messages in this channel
2. /summary
    ⇒ Produce daily summaries in a time frame
    ⇒ Arguments:
        ⇒ None (default)
            ⇒ produce daily summaries for the past 7 days
        ⇒ <date>
            ⇒ produce summary for date 
            ⇒ e.g. /summary 2023-07-05
        ⇒ <start_date> <end_date>
            ⇒ produce daily summaries from <start_date> to <end_date> 
            ⇒ e.g. /summary 2023-07-02 2023-07-05
        ⇒ <start_date> <number_of_days>
            ⇒ produce daily summaries from <start_date> to <number_of_days> in future 
            ⇒ e.g. /start 2023-07-02 2 ⇒ summary of 07-02, 07-03
3. /clean
    ⇒ Dedupe and remove bad chars from the raw messages
        ⇒ Recommend running before /summary to ensure best output
4. /both
    ⇒ Runs /clean and /summary
    ⇒ Arguments:
        ⇒ Same as /summary
5. /prompt
    ⇒ request information from ATL BitLab Bot
    ⇒ Arguments:
        <statement>
            ⇒ declare a statement
            ⇒ e.g. ATL BitLab rocks!
        <request>
            ⇒ make a request
            ⇒ e.g. This sentence is short. Send a shorter one.
        <question>
            ⇒ ask a question
            ⇒ e.g. What is the answer to the ultimate question of life, the universe, and everything?
6. /help
    ⇒ Show this help menu"""