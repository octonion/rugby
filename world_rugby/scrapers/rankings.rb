#!/usr/bin/env ruby

require 'mechanize'
require 'json'

agent = Mechanize.new{ |agent| agent.history.max_size=0 }
agent.user_agent = 'Mozilla/5.0'
agent.robots = false

url = "http://cmsapi.pulselive.com/rugby/rankings/mru.json"

unparsed_json = agent.get(url).body

parsed_json = JSON.parse(unparsed_json)

File.write("json/rankings.json",parsed_json.to_json)
