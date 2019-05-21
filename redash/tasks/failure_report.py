import datetime
from collections import Counter
from redash.tasks.general import send_mail
from redash.worker import celery
from redash import redis_connection, settings
from redash.utils import json_dumps, json_loads, base_url


@celery.task(name="redash.tasks.send_aggregated_errors")
def send_aggregated_errors(email_address):
    key = 'aggregated_failures:{}'.format(email_address)
    errors = [json_loads(e) for e in redis_connection.lrange(key, 0, -1)]
    errors.reverse()
    occurrences = Counter((e.get('id'), e.get('message')) for e in errors)
    unique_errors = {(e.get('id'), e.get('message')): e for e in errors}

    failures_html = ''.join(["""
		<div style="background: white;padding: 5px 20px 20px 20px; border-radius: 3px; box-shadow: 0 4px 9px -3px rgba(102,136,153,.15); margin-top: 20px">
			<h2 style="font-size: 16px; position: relative">{name} <a href="{base_url}/queries/{id}" style="background-color: #ff7964;font-size: 13px;color:  white;text-decoration: none;padding: 0 5px;display: inline-block;border-radius: 3px;font-weight: normal;position: absolute;right: 0;top:-1px">Go
					to Query</a></h2>
			<div>
				<p>
					Last failed: {failed_at}
					<br />
					<small style="color: #8c8c8c;font-size: 13px;">&nbsp; + {failure_count} more failures since last report</small>
				</p>
				<h3 style="font-size: 14px; font-weight:normal; margin-bottom: 6px">Exception</h3>
				<div style="background: #ececec;padding: 8px;border-radius: 3px;font-family: monospace;">{failure_reason}</div>
			</div>
			<div style="margin-top: 25px;font-size: 13px;border-top: 1px solid #ececec;padding-top: 19px;">{comment}</div>
		</div>""".format(
                base_url=v.get('base_url'),
                id=v.get('id'),
                name=v.get('name'),
                failed_at=v.get('failed_at'),
                failure_reason=v.get('message'),
                failure_count=occurrences[k],
                comment=v.get('comment')) for k, v in unique_errors.iteritems()])

    html = """
        <html>
    
            <head>
            	<style>
            		body {{
            			margin: 0;
            		}}
            	</style>
            </head>
            
            <body style="margin: 0;">
            	<div style="background: #f6f8f9; font-family: arial; font-size: 14px; padding: 20px; color: #333; line-height: 20px">
            		<div style="padding-bottom: 23px; margin-bottom: 22px; border-bottom: 1px solid #e4e4e4;">
            			<img height="50" src="data:image/png;base64,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" />
            		</div>
            		<h1 style="font-size: 14px; font-weight: normal;">Redash failed to run the following queries:</h1>
                    {}
            	</div>
            </body>
        
        </html>""".format(failures_html)

    send_mail.delay([email_address], "Redash failed to execute {} of your queries".format(len(unique_errors.keys())), html, None)

    redis_connection.delete(key)


def notify_of_failure(message, query):
    if not settings.SEND_EMAIL_ON_FAILED_SCHEDULED_QUERIES:
        return

    if query.schedule_failures < settings.MAX_FAILURE_REPORTS_PER_QUERY:
        key = 'aggregated_failures:{}'.format(query.user.email)
        reporting_will_soon_stop = query.schedule_failures > settings.MAX_FAILURE_REPORTS_PER_QUERY * 0.75
        comment = """This query has failed a total of {failure_count} times.
                     Reporting may stop when the query exceeds {max_failure_reports} overall failures.""".format(
            failure_count=query.schedule_failures,
            max_failure_reports=settings.MAX_FAILURE_REPORTS_PER_QUERY
        ) if reporting_will_soon_stop else ''

        redis_connection.lpush(key, json_dumps({
            'id': query.id,
            'name': query.name,
            'base_url': base_url(query.org),
            'message': message,
            'comment': comment,
            'failed_at': datetime.datetime.utcnow().strftime("%B %d, %I:%M%p UTC")
        }))

        if not redis_connection.exists('{}:pending'.format(key)):
            send_aggregated_errors.apply_async(args=(query.user.email,), countdown=settings.SEND_FAILURE_EMAIL_INTERVAL)
            redis_connection.set('{}:pending'.format(key), 1)
            redis_connection.expire('{}:pending'.format(key), settings.SEND_FAILURE_EMAIL_INTERVAL)
