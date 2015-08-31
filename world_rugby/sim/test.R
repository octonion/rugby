f = function(k,r1,r2,p1,p2,UB)  
{

  S=0
  const = (p1^k) * ((1-p1)^r1) * ((1-p2)^r2)
  const = const/( factorial(r1-1) * factorial(r2-1) ) 

  for(y in 0:UB)
  {
     iy = ((p1*p2)^y) * factorial(y+r2-1)*factorial(k+y+r1-1)
     iy = iy/( factorial(y)*factorial(y+k) )
     S = S + iy
  }

  return(S*const)
}

 ### Sims
 
 r1 = 6; r2 = 4; 
 p1 = .7; p2 = .53; 
 X = rnbinom(1e5,r1,p1)
 Y = rnbinom(1e5,r2,p2)
 mean( (X-Y) == 2 ) 
 
 f(2,r1,r2,1-p1,1-p2,20)
 
 mean( (X-Y) == 1 ) 
 
 f(1,r1,r2,1-p1,1-p2,20)
 
 mean( (X-Y) == 0 ) 
 
 f(0,r1,r2,1-p1,1-p2,20)
 