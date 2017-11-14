import ring
cache_dict = {}

@ring.func.dict(cache_dict)
def mytest(a):
    return a + 3

@ring.func.dict(cache_dict)
def mytest2(a):
    return a +4

print(mytest(3)) # 6
print(mytest2(3)) # 6 : bug