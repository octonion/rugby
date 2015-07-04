#!/usr/bin/env ruby

require 'mechanize'
require 'json'
require 'csv'

agent = Mechanize.new{ |agent| agent.history.max_size=0 }
agent.user_agent = 'Mozilla/5.0'
agent.robots = false

sports = CSV.open("csv/sports.csv","w")
types = CSV.open("csv/types.csv","w")
results = CSV.open("csv/countries.csv","w")

page_size = 100

#countries = JSON.parse(unparsed_json)

country_meta = JSON.parse(File.open("json/country_meta.json").read())

#countries = JSON.parse(File.open("json/country_meta.json").read())

#p country_meta.keys
#p country_meta["pageInfo"]
#p country_meta["content"].keys
#p country_meta["content"]["countries"][0].keys

# country_meta["content"].keys
# sportLookup, typeLookup, countries

country_meta["content"]["sportLookup"].each do |sport|
  sports << sport
end

country_meta["content"]["typeLookup"].each do |type|
  types << type
end

# id, name, teams

n = country_meta["pageInfo"]["numPages"].to_i

pages = (n.to_f/page_size).ceil

(0..pages-1).each do |page_num|

  begin
    url = "http://cmsapi.pulselive.com/rugby/country.json?pageSize=#{page_size}&page=#{page_num}"
    unparsed_json = agent.get(url).body
    parsed_json = JSON.parse(unparsed_json)
  rescue
    sleep 5
    print "Retry ...\n"
    retry
  end
  
  parsed_json["content"]["countries"].each do |country|

    country_id = country["id"].to_i
    country_name = country["name"]
    country_json = country["teams"]
    results << [country_id, country_name, country_json.to_json]
    
  end
  results.flush
  
end

results.close

#p countries.keys
#p countries["content"].keys

#p countries["content"]["countries"][0]["id"]
#p countries["content"]["countries"][0]["name"]

#countries["content"].each do |c|
#  p c
#end
