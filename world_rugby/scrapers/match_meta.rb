#!/usr/bin/env ruby

require 'mechanize'
require 'json'

agent = Mechanize.new{ |agent| agent.history.max_size=0 }
agent.user_agent = 'Mozilla/5.0'
agent.robots = false

year = ARGV[0]

url = "http://cmsapi.pulselive.com/rugby/match.json?endDate=#{year}-12-31&startDate=#{year}-01-01&sort=desc&page=0&pageSize=1"

unparsed_json = agent.get(url).body

parsed_json = JSON.parse(unparsed_json)

File.write("json/match_meta_#{year}.json",parsed_json.to_json)
