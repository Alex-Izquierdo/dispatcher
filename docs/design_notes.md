## Reference Designs

### AWX dispatcher

This is directly taken from the AWX dispatcher.

https://github.com/ansible/awx/tree/devel/awx/main/dispatch

This was introduced in:

https://github.com/ansible/awx/pull/2266

> ...much like the callback receiver implementation in 3.3.0 (on which this code is based), this entry point is a kombu.ConsumerMixin.

### Kombu

Kombu is a sub-package of celery.

https://github.com/celery/kombu

In messaging module, this has a `Producer` and `Consumer` classes.
In mixins it has a `ConsumerMixin`, but no methods seem to have made it into AWX dispatch.

This doesn't deal with worker pool management. It does have examples with `Worker` classes.
These follow a similar contract with `process_task` here.

### AMQP

https://www.rabbitmq.com/tutorials/amqp-concepts

This protcol deals with publishers, exchanges, queues, and consumers.

### ProcessPoolExecutor

The python `ProcessPoolExecutor` uses both a single call queue and a single results queue.

https://github.com/python/cpython/blob/f1d33dbddd3496b062e1fbe024fb6d7b023a35f5/Lib/concurrent/futures/process.py#L217

Some things it does is not applicable to the dispatcher here, because it strives to adhere
to an existing contract around python futures that we do not care about.

The local worker thread has many commonalities to the results thread being used here.
It is most interesting to the the three-fold criteria for wakeups in that thread:

```python
result_item, is_broken, cause = self.wait_result_broken_or_wakeup()
```

By comparision, the results thread used here only has 1 condition.
In some shutdown or recycle cases, it may be canceled.

An important similarity is that the manager maintains an internal working queue.
This is also done in this library, and diverges from AWX practice.
In AWX dispatcher, a full queue may put messages into individual worker IPCs.
This caused bad results, like delaying tasks due to long-running jobs,
while the pool had many other workers free up in the mean time.

## Alternative Archectures

This are blue-sky ideas, which may not happen anytime soon,
but they are described to help structure the app today so it can expand
into these potential future roles.

### Singleton task queue

A major pivot from the AWX dispatcher is that we do not use 1 result queue per worker,
but a single result queue for all workers, and each meassage includes a worker id.

If you continue this pattern, then we would no longer have a call queue for each worker,
and workers would just grab messages from the queue as they are available.

The problem you encounter is that you will not know what worker started what task.
If you do any "management" this is a problem. For instance, if you want a task
to have a timeout, you need to know which worker to kill if it goes over its limit.

There is a way to still consolidate the call queue while no losing these other features.
When a worker receives a task, it can submit an ACK to the finished queue telling
the main process that it has started a task, and which task it started.

This isn't ultimately robust, if there is an error between getting the message and ACK,
but this probably isn't a reasonable concern. As of now, this looks viable.

### Persistent work manager

Years ago, when AWX was having trouble with output processing bottlenecks,
we stopped using the main dispatcher process to dispatch job events to workers.

Essentially, any performance-sensitive data volumes should not go through the
pool worker management system where data is passed through IPC queues.
Doing this causes the main process to be a bottleneck.

The solution was to have workers connect to a socket on their own.

Nothing is wrong with this, it's just weird.
None of the written facilities for pool management in dispatcher code is useful.
Because of that, event processing diverged far from the rest of the dispatcher.

Long-term vision here is that:
 - a `@task` decorator may mark a task as persistent
 - additional messages types will need to be send into the finished queue for
   - analytics tracking, like how many messages were processed
   - whether a particular resource being monitored has been closed

The idea is that this would integrate what was prototyped in:

https://github.com/AlanCoding/receptor-reporter/tree/devel

That idea involved the main process more than the existing callback receiver.
Because each job has its own socket that has to be read from, so these will come and go.
And a worker may manage more than 1 job at the same time, asynchronously.

This also requires forking from what is now `dispatcher.main`.
We could keep the pool (and add more feature) but this requires
an entirely different main loop.
