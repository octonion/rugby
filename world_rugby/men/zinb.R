sink("diagnostics/zinb.txt")

#library(glmmADMB)
library(glmmTMB)
library(RPostgreSQL)

drv <- dbDriver("PostgreSQL")
con <- dbConnect(drv,dbname="rugby")

query <- dbSendQuery(con, "
select

*

from
(
select
distinct
r.game_id,
r.year,
r.field as field,
r.team_id as team,
r.opponent_id as opponent,
--r.game_length as game_length,
team_score::float as gs,
(year-2020) as w
from men._results r

where
    r.year between 2021 and 2025

--and r.team_id in
--(
--select
--team_id
--from men._results
--where year between 2013 and 2021
--group by team_id
--having count(*)>=6
--)

--and r.opponent_id in
--(
--select
--team_id
--from men._results
--where year between 2013 and 2021
--group by team_id
--having count(*)>=6
--)
) as r

order by random()

;")

sg <- fetch(query,n=-1)

dim(sg)

games <- sg[rep(row.names(sg), sg$w), ]

#games <- sg

dim(games)

attach(games)

pll <- list()

# Fixed parameters

field <- as.factor(field)
field <- relevel(field, ref = "neutral")

#game_length <- as.factor(game_length)

fp <- data.frame(field) #,game_length)
fpn <- names(fp)

# Random parameters

game_id <- as.factor(game_id)
#contrasts(game_id) <- 'contr.sum'

offense <- as.factor(team)
#contrasts(offense) <- 'contr.sum'

defense <- as.factor(opponent)
#contrasts(defense) <- 'contr.sum'

rp <- data.frame(offense,defense)
rpn <- names(rp)

for (n in fpn) {
  df <- fp[[n]]
  level <- as.matrix(attributes(df)$levels)
  parameter <- rep(n,nrow(level))
  type <- rep("fixed",nrow(level))
  pll <- c(pll,list(data.frame(parameter,type,level)))
}

for (n in rpn) {
  df <- rp[[n]]
  level <- as.matrix(attributes(df)$levels)
  parameter <- rep(n,nrow(level))
  type <- rep("random",nrow(level))
  pll <- c(pll,list(data.frame(parameter,type,level)))
}

# Model parameters

parameter_levels <- as.data.frame(do.call("rbind",pll))
dbWriteTable(con,c("men","_zinb_parameter_levels"),parameter_levels,row.names=TRUE)

g <- cbind(fp,rp)
g$gs <- gs
#g$w <- w

#detach(games)

dim(g)

model <- gs ~ field + (1|offense) + (1|defense) + (1|game_id)

#fit0 <- glmmadmb(model, data=g, zeroInflation=FALSE, family="nbinom", verbose=TRUE)

#fit0
#summary(fit0)

fit <- glmmTMB(model, data=g, ziformula=~1, family=nbinom1, verbose=TRUE)

fit
summary(fit)

#anova(fit0,fit)
#str(fit)

# List of data frames

# Fixed factors

f <- fixef(fit)
fn <- names(f)

print(fn)

# Random factors

r <- ranef(fit)
rn <- names(r)

results <- list()

for (n in fn) {

  df <- f[[n]]
  
  factor <- n
  level <- n
  type <- "fixed"
  estimate <- df

  results <- c(results,list(data.frame(factor,type,level,estimate)))

 }

print(results)

for (n in rn) {

  df <- r[[n]]

  factor <- rep(n,nrow(df))
  type <- rep("random",nrow(df))
  level <- row.names(df)
  estimate <- df[,1]

  results <- c(results,list(data.frame(factor,type,level,estimate)))

 }

results <- c(results,list(data.frame(factor="pz",type="structural",level="pz",estimate=fit$pz)))
results <- c(results,list(data.frame(factor="alpha",type="structural",level="alpha",estimate=fit$alpha)))

combined <- as.data.frame(do.call("rbind",results))

dbWriteTable(con,c("men","_zinb_basic_factors"),as.data.frame(combined),row.names=TRUE)

quit("no")
