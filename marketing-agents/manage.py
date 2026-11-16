import argparse
from contextlib import closing
import os
import app
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Set the monthly run allowance for a company.')
    parser.add_argument('company_id',type=int);parser.add_argument('tier',choices=app.LIMITS)
    args=parser.parse_args()
    os.umask(0o077)
    with closing(app.db()) as c, c:
        if not c.execute('update org set tier=? where id=?',(args.tier,args.company_id)).rowcount: parser.error('No such company')
