# Using Redis for Caching Data in Django

Data drives web applications. On the server, data moves between the application and the database, and in Django, the ORM is primarily used to construct those queries. Unfortunately, querying a database takes a toll on application performance. The more times the application calls the database during an HTTP request, the longer it takes to return a response. In an environment where <a href="https://www.nngroup.com/articles/response-times-3-important-limits/">users expect website response times of less than a second</a>, every database query affects the user experience.

Since many <a href="https://www.digitalocean.com/community/tutorials/5-common-server-setups-for-your-web-application">common server setups</a> separate the application from the database, Django must make a network call to retrieve data. Network latency plays a substantial role in the amount of time it takes for the ORM to execute database queries. 

> Latency is the amount of time needed to send information from one point to another. 

Given the direct relationship between the number of network calls and the time it takes for them to resolve, reducing that number should improve application performance.

One way to reduce the number of network calls is by caching data that does not change very often yet is frequently queried. Using a cache gives Django the ability to make a single network call (to the cache) instead of multiple calls to the database. 

In the following tutorial, I will demonstrate how to use Redis as a cache for Django. First, I will show you how to inspect the number of database queries your application is making without the cache in place. Next, I will walk you through the process of setting up and using the Redis server and the Redis CLI in conjunction with your Django application. Lastly, I will explain how to use the Django Debug Toolbar to conveniently monitor what network calls are being made when your application APIs are accessed.
