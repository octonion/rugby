#!/usr/bin/env ruby

require 'mechanize'
require 'json'
require 'csv'

# "matchId":21744
# "description":"Match 1"
# "eventPhase":"Pool C"
# "venue":
#   {"id":348
#    "name":"Stadio Sergio Lanfranchi"
#    "city":"Parma"
#    "country":"Italy"}
# "time":
#   {"millis":1433255400000
#    "gmtOffset":2.0
#    "label":"Tue 2 Jun 2015, 16:30 GMT+02:00"}
# "attendance":3287
# "teams":
#   [{"id":2749,"name":"Ireland","abbreviation":"IRE"},
#    {"id":2748,"name":"Argentina","abbreviation":"ARG"}]
# "scores":[18,16]
# "status":"C"
# "outcome":"A"
# "events":
#   [{"id":1566
#     "label":"World Rugby U20 Championship 2015"
#     "sport":"jm"
#     "start":{"millis":1433203200000,"label":"2015-06-02"}
#     "end":{"millis":1434844799000,"label":"2015-06-20"}}]

agent = Mechanize.new{ |agent| agent.history.max_size=0 }
agent.user_agent = 'Mozilla/5.0'
agent.robots = false

page_size = 100

first_year = ARGV[0].to_i

if (ARGV[1] == nil)
  last_year = first_year
else
  last_year = ARGV[1].to_i rescue nil
end

(first_year..last_year).each do |year|

  found = 0

  print "Matches for year #{year} ..."

  results = CSV.open("csv/matches_#{year}.csv", "w")

  match_meta = JSON.parse(File.open("json/match_meta_#{year}.json").read())

  n = match_meta["pageInfo"]["numPages"].to_i

  pages = (n.to_f/page_size).ceil

  (0..pages-1).each do |page_num|

    begin
      url = "http://cmsapi.pulselive.com/rugby/match.json?startDate=#{year}-01-01&endDate=#{year}-12-31&sort=asc&pageSize=#{page_size}&page=#{page_num}"
      unparsed_json = agent.get(url).body
      parsed_json = JSON.parse(unparsed_json)
    rescue
      sleep 5
      print " retry ..."
      retry
    end
  
    parsed_json["content"].each do |match|

      match_id = match["matchId"].to_i rescue nil
      description = match["description"] rescue nil
    
      venue_id = match["venue"]["id"] rescue nil
      venue_name = match["venue"]["name"] rescue nil
      venue_city = match["venue"]["city"] rescue nil
      venue_country = match["venue"]["country"] rescue nil
    
      time_millis = match["time"]["millis"] rescue nil
      time_gmtoffset = match["time"]["millis"] rescue nil
      time_label = match["time"]["label"] rescue nil

      attendance = match["attendance"] rescue nil

      team_id = match["teams"][0]["id"] rescue nil
      team_name = match["teams"][0]["name"] rescue nil
      team_abbr = match["teams"][0]["abbreviation"] rescue nil

      opponent_id = match["teams"][1]["id"] rescue nil
      opponent_name = match["teams"][1]["name"] rescue nil
      opponent_abbr = match["teams"][1]["abbreviation"] rescue nil

      team_score = match["scores"][0] rescue nil
      opponent_score = match["scores"][1] rescue nil

      status = match["status"] rescue nil

      outcome = match["outcome"] rescue nil
    
      events_id = match["events"][0]["id"] rescue nil
      events_label = match["events"][0]["label"] rescue nil
      events_sport = match["events"][0]["sport"] rescue nil
      events_start_millis = match["events"][0]["start"]["millis"] rescue nil
      events_start_label = match["events"][0]["start"]["label"] rescue nil
      events_end_millis = match["events"][0]["end"]["millis"] rescue nil
      events_end_label = match["events"][0]["end"]["label"] rescue nil
    
      results << [match_id, description,
                  venue_id, venue_name, venue_city, venue_country,
                  time_millis, time_gmtoffset, time_label,
                  attendance,
                  team_id, team_name, team_abbr, 
                  opponent_id, opponent_name, opponent_abbr,
                  team_score, opponent_score,
                  status, outcome,
                  events_id, events_label, events_sport,
                  events_start_millis, events_start_label,
                  events_end_millis, events_end_label,
                  match.to_json]

      found += 1
    
    end

    results.flush

  end
  print " #{found} matches\n"
  results.close
  
end

